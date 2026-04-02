"""
Sentinel Security Gateway - HTTP Server

FastAPI server that exposes the Sentinel runtime as an HTTP API.
The OpenClaw plugin calls this server to audit commands through the full
ADK/LLM semantic analysis pipeline.

Usage:
    python sentinel_server.py

The server runs on http://localhost:8765 by default.
"""

from __future__ import annotations

import json
import os
import time
import uuid
import httpx
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import the Sentinel runtime
from src.sentinel.main import SentinelRuntime, AuditDecision
from src.governance.approvals import ApprovalManager, PendingRequest
from src.sentinel.logger import audit_logger
from src.sentinel.redactor import redactor
from src.sentinel.inference_broker import inference_broker

# --- Sentinel AIOps & Governance Imports ---
from src.ledger.ledger_service import allocate_internal_credit, allocate_service_credit, spend_service_credit
from src.ledger.ledger import read_wallets, ACCOUNTING_LOG
from src.ledger.oracle import get_current_rate
from src.analytics.aggregator import AnalyticsAggregator

app = FastAPI(
    title="Sentinel Security Gateway",
    description="HTTP API for command auditing with deterministic + LLM semantic analysis",
    version="2.0.0",
)


def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("SENTINEL_ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1,http://localhost:4200")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost", "http://127.0.0.1", "http://localhost:4200"]


def _requires_auth() -> bool:
    return os.getenv("SENTINEL_DISABLE_AUTH", "false").strip().lower() not in {"1", "true", "yes"}


def _get_auth_token() -> Optional[str]:
    token = os.getenv("SENTINEL_AUTH_TOKEN", "").strip()
    return token or None

# Allow CORS for local development (OpenClaw plugin calls from localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Angular Dashboard
# Serve the browser build directory
app.mount("/dashboard", StaticFiles(directory="web/dist/browser", html=True), name="dashboard")

# Initialize the Sentinel runtime once at startup
runtime: Optional[SentinelRuntime] = None
approval_manager = ApprovalManager()
analytics_aggregator = AnalyticsAggregator()


class AuditRequest(BaseModel):
    """Request body for command auditing."""
    command: str
    agent_id: str
    wallet_id: Optional[str] = None
    project_id: Optional[str] = "default"
    estimated_cost_jul: Optional[float] = 0.0
    risk_score: Optional[int] = None


class AuditResponse(BaseModel):
    """Response body from command auditing."""
    allowed: bool
    risk_score: int
    reason: str
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


def _verify_auth(x_sentinel_token: Optional[str]) -> None:
    if not _requires_auth():
        return

    expected_token = _get_auth_token()
    if not expected_token:
        raise HTTPException(status_code=503, detail="Sentinel auth token is not configured")

    if x_sentinel_token != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.on_event("startup")
async def startup_event():
    """Initialize Sentinel runtime on server startup."""
    global runtime
    try:
        runtime = SentinelRuntime()
        if runtime.startup_warning:
            print(f"⚠️  Sentinel warning: {runtime.startup_warning}")
        print("🛡️  Sentinel Security Gateway initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Sentinel: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sentinel"}


@app.post("/audit", response_model=AuditResponse)
def audit_command(request: AuditRequest, x_sentinel_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """
    Audit a shell command through Sentinel's security layers.
    
    Layer 1: Deterministic blocklist (<1ms)
    Layer 2: LLM semantic analysis (~500ms) if available
    
    Returns audit decision with execution results if approved.
    """
    if runtime is None:
        raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")

    _verify_auth(x_sentinel_token)
    start_time = time.time()
    
    if not request.command or not request.command.strip():
        return {
            "allowed": False,
            "risk_score": 10,
            "reason": "Empty command",
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }
    
    correlation_id = str(uuid.uuid4())
    try:
        result = runtime.run_intercepted_command(request.command, correlation_id=correlation_id)
        result["correlation_id"] = correlation_id
        
        # HITL Hook
        if result.get("status") == "review_required":
            req_id = approval_manager.create_request(
                command=request.command, 
                rule_name="Policy Review",
                reason=result.get("reason", "Requires approval"),
                wallet_id=request.wallet_id or request.agent_id,
                agent_id=request.agent_id,
                project_id=request.project_id or "default",
                estimated_cost_jul=request.estimated_cost_jul or 0.0,
                risk_score=result.get("risk_score", request.risk_score or 0)
            )
            result["reason"] = f"{result.get('reason')} [Request ID: {req_id}]"
            print(f"⚠️  Review Required. Request ID: {req_id}")

        duration_ms = (time.time() - start_time) * 1000
        print(f"⏱️  Audit completed in {duration_ms:.2f}ms. Decision: {'✅' if result['allowed'] else '❌'} ({result.get('reason', 'No reason provided')})")
        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        print(f"❌ Audit failed in {duration_ms:.2f}ms: {e}")
        raise


@app.post("/audit-only")
def audit_only(request: AuditRequest, x_sentinel_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """
    Audit a command WITHOUT executing it.
    Returns the audit decision only.
    """
    if runtime is None:
        raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")

    _verify_auth(x_sentinel_token)
    
    correlation_id = str(uuid.uuid4())
    # Use the command auditor directly for audit-only
    decision: AuditDecision = runtime.command_auditor.audit(request.command)
    res = decision.to_dict()
    res["correlation_id"] = correlation_id
    return res


@app.post("/v1/chat/completions")
async def chat_proxy(request: ChatCompletionRequest, x_sentinel_token: Optional[str] = Header(default=None)):
    """
    OpenAI-compatible chat completions proxy with Sentinel auditing.
    """
    if runtime is None:
        raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")

    _verify_auth(x_sentinel_token)

    # --- Epic 1: Sovereign Scrub Middleware ---
    # Intercept and sanitize all incoming agent messages BEFORE they hit the cloud
    for msg in request.messages:
        if msg.content:
            clean_text, metrics = scrub_payload(msg.content)
            if metrics.get("estimated_tokens_saved", 0) > 0 or metrics.get("redactions_applied"):
                 print(f"🛡️ [SCRUB] Saved {metrics.get('estimated_tokens_saved', 0)} tokens. Redactions: {metrics.get('redactions_applied', {})}")
            msg.content = clean_text

    # 1. Extract Prompt for Auditing
    full_prompt = "\n".join([f"{m.role}: {m.content}" for m in request.messages])
    
    # 2. Pre-Inference Audit
    correlation_id = str(uuid.uuid4())
    decision = runtime.audit_text(full_prompt, is_completion=False)
    
    if not decision.allowed:
        audit_logger.log_event(
            event_type="normalized_input",
            input_str=full_prompt,
            correlation_id=correlation_id,
            decision="block",
            reason=decision.reason,
            metadata={"risk_score": decision.risk_score}
        )
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "Sentinel blocked this prompt",
                "reason": decision.reason,
                "risk_score": decision.risk_score,
                "correlation_id": correlation_id
            }
        )

    # 3. Determine Upstream Provider and Creds
    model_name = request.model.lower()
    url = "https://openrouter.ai/api/v1/chat/completions"
    api_key = os.getenv("OPEN_ROUTER_API_KEY")

    if "nvidia" in model_name:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        api_key = os.getenv("NVIDIA_API_KEY")
    elif "gemini" in model_name or model_name.startswith("google/"):
        # If the user wants direct Gemini API
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise HTTPException(status_code=500, detail=f"No API key configured for model {request.model}")

    # 4. Forward to Provider
    async with httpx.AsyncClient() as client:
        try:
            # Prepare headers with host-side API key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            # Special headers for OpenRouter
            if "openrouter" in url:
                headers["HTTP-Referer"] = "https://sentinel.security"
                headers["X-Title"] = "Sentinel Security Gateway"

            upstream_response = await client.post(
                url,
                json=request.model_dump(),
                headers=headers,
                timeout=60.0
            )
            
            if upstream_response.status_code != 200:
                print(f"❌ Upstream error ({upstream_response.status_code}): {upstream_response.text}")
                raise HTTPException(status_code=upstream_response.status_code, detail=upstream_response.text)

            # Shape the response for internal consumption (Layer 4 Hardening)
            raw_response = upstream_response.json()
            shaped_response = inference_broker.shape_response(raw_response)
            
            # Generate request signature for internal audit correlation
            sig = inference_broker.sign_request(json.dumps(shaped_response))
            
            audit_logger.log_event("inference_completion", {
                "request_id": str(correlation_id), # Changed from request_id to correlation_id
                "model": shaped_response.get("model"),
                "token_usage": shaped_response.get("usage"),
                "status": "success",
                "signature": sig
            })
            
            # Return redacted content to the agent
            redacted_content = redactor.redact(shaped_response.get("content", ""))
            
            # --- Sentinel AIOps: Record Agent Spend ---
            # Automatically account for the cost of this inference as "Utility" spend
            usage = shaped_response.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            if total_tokens > 0:
                try:
                    # Map tokens to internal AIOps credits (JOULE)
                    # 1000 tokens = ~0.01 JOULE (Example calculation)
                    estimated_jul = (total_tokens / 1000) * 0.01 
                    
                    record_agent_spend(
                        agent_id="+27658623499", # Project default agent
                        amount_jul=round(estimated_jul, 6),
                        category="utility",
                        project_id="taajirah_internal",
                        agent_run_id=str(correlation_id),
                        notes=f"Inference: {model_name}"
                    )
                except Exception as e:
                    print(f"⚠️ [AIOps] Failed to record agent spend: {e}")

            return {
                "id": shaped_response.get("id"),
                "choices": [{"message": {"content": redacted_content}}],
                "usage": shaped_response.get("usage")
            }

        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Upstream request failed: {exc}")


@app.get("/pending", response_model=Dict[str, PendingRequest])
def list_pending_requests(x_sentinel_token: Optional[str] = Header(default=None)):
    """List all pending approval requests."""
    _verify_auth(x_sentinel_token)
    return approval_manager.list_pending()


@app.post("/approve/{request_id}")
def approve_request(
    request_id: str, 
    actor_id: str = "human_operator",
    reason: str = "Manual Approval",
    x_sentinel_token: Optional[str] = Header(default=None)
):
    """Approve and execute a pending request."""
    _verify_auth(x_sentinel_token)
    
    req = approval_manager.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")
    
    # Check expiry
    if time.time() > req.expires_at:
        approval_manager.cleanup_old_requests() # Triggers purge
        raise HTTPException(status_code=410, detail="Request has expired")

    print(f"✅ Approving request {request_id} by {actor_id}: {req.command}")
    
    # --- Sentinel AIOps: Reward Human Oversight ---
    try:
        allocate_internal_credit(
            wallet_id=actor_id, 
            contribution_type="verification",
            correlation_id=request_id,
            approved_by="system",
            notes=f"Validated command: {req.command[:30]}..."
        )
    except Exception as e:
        print(f"⚠️ [AIOps] Failed to allocate oversight credit: {e}")
    
    # Execute with policy bypass
    try:
        if runtime is None:
             raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")
             
        result = runtime.run_intercepted_command(req.command, bypass_policy=True)
        approval_manager.resolve_request(request_id, "approved", actor_id=actor_id, reason=reason)
        return result
    except Exception as e:
        print(f"❌ Execution failed for approved request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
def get_audit_logs(limit: int = 50, x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch recent audit logs from the structured audit logger."""
    _verify_auth(x_sentinel_token)
    
    # In v2.2, we use JSONL file logs. This endpoint could be extended to read them.
    return {"message": "Logs are available at sentinel/logs/audit_structured.jsonl"}


# --- JOULE Admin Dashboard Routes ---

@app.get("/api/admin/wallets")
def admin_get_wallets(x_sentinel_token: Optional[str] = Header(default=None)):
    """Return all wallets and their balances."""
    _verify_auth(x_sentinel_token)
    return {"wallets": read_wallets()}

@app.get("/api/admin/transactions")
def admin_get_transactions(x_sentinel_token: Optional[str] = Header(default=None)):
    """Read the transaction JSONL log."""
    _verify_auth(x_sentinel_token)
    txs = []
    if TRANSACTION_LOG.exists():
        with open(TRANSACTION_LOG, "r") as f:
            for line in f:
                if line.strip():
                    txs.append(json.loads(line))
    # Return newest first
    return {"transactions": list(reversed(txs))}

@app.post("/api/admin/settlements/{request_id}/approve")
def admin_approve_settlement_route(request_id: str, x_sentinel_token: Optional[str] = Header(default=None)):
    """Approve a pending withdrawal/settlement request."""
    _verify_auth(x_sentinel_token)
    try:
        from src.ledger.wallet import approve_withdrawal
        updated_event = approve_withdrawal(request_id, approved_by="admin_dashboard")
        return {"status": "success", "event": updated_event}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/admin/oracle")
def admin_get_oracle(x_sentinel_token: Optional[str] = Header(default=None)):
    """Return live AIOps settlement index."""
    _verify_auth(x_sentinel_token)
    return {
        "zar_rate": get_current_rate(),
        "description": "Administrative compute metering index (1 JOULE = 1 ZAR)",
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

class AllocationRequest(BaseModel):
    recipient: str
    amount_jul: float
    reference: str = ""

@app.post("/api/admin/treasury/allocate")
def admin_allocate_treasury(payload: AllocationRequest, x_sentinel_token: Optional[str] = Header(default=None)):
    """Allocate new service credits into an entity's wallet based on actual fiat deposits."""
    _verify_auth(x_sentinel_token)
    try:
        if payload.amount_jul <= 0:
            raise ValueError("Allocation amount must be > 0")
        
        record = allocate_service_credit(
            wallet_id=payload.recipient,
            amount_jul=payload.amount_jul,
            approved_by="admin_dashboard",
            reference=payload.reference or str(uuid.uuid4())
        )
        return {"status": "success", "issuance": record}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
class ComplianceUpdateRequest(BaseModel):
    wallet_id: str
    actor_id: str
    reason: str
    kyc_verified: Optional[bool] = None
    contract_active: Optional[bool] = None
    reputation_score: Optional[float] = None
    monthly_settlement_limit_zar: Optional[float] = None
    budget_limit_jul: Optional[float] = None

@app.post("/api/admin/wallets/compliance/update")
def admin_compliance_update(payload: ComplianceUpdateRequest, x_sentinel_token: Optional[str] = Header(default=None)):
    """Update a wallet's compliance flags and limits using strictly audited events."""
    _verify_auth(x_sentinel_token)
    from src.ledger.ledger import read_wallets, write_wallets, write_compliance_event
    from datetime import datetime, timezone
    
    if not payload.actor_id:
        raise HTTPException(status_code=400, detail="ERR_ADMIN_AUTH_REQUIRED: actor_id is required.")
    if not payload.reason:
        raise HTTPException(status_code=400, detail="ERR_REASON_REQUIRED: A valid semantic reason is required.")
        
    wallets = read_wallets()
    if payload.wallet_id not in wallets:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    wallet = wallets[payload.wallet_id]
    old_state = wallet.copy()
    
    updates = {}
    if payload.kyc_verified is not None and wallet.get("kyc_verified") != payload.kyc_verified:
        updates["kyc_verified"] = payload.kyc_verified
    if payload.contract_active is not None and wallet.get("contract_active") != payload.contract_active:
        updates["contract_active"] = payload.contract_active
    if payload.reputation_score is not None and wallet.get("reputation_score") != payload.reputation_score:
        updates["reputation_score"] = payload.reputation_score
        wallet["reputation_last_updated_at"] = datetime.now(timezone.utc).isoformat()
        wallet["reputation_last_updated_by"] = payload.actor_id
    if payload.monthly_settlement_limit_zar is not None and wallet.get("monthly_settlement_limit_zar") != payload.monthly_settlement_limit_zar:
        updates["monthly_settlement_limit_zar"] = payload.monthly_settlement_limit_zar
    if payload.budget_limit_jul is not None and wallet.get("budget_limit_jul") != payload.budget_limit_jul:
        updates["budget_limit_jul"] = payload.budget_limit_jul
        
    if not updates:
        return {"status": "unchanged", "wallet": wallet}
        
    for k, v in updates.items():
        wallet[k] = v
        
    wallet["compliance_last_updated_at"] = datetime.now(timezone.utc).isoformat()
    wallet["compliance_last_updated_by"] = payload.actor_id
        
    # Append-only ledger event
    write_compliance_event({
        "event_type": "admin_compliance_update",
        "timestamp": wallet["compliance_last_updated_at"],
        "actor_id": payload.actor_id,
        "wallet_id": payload.wallet_id,
        "reason": payload.reason,
        "old_values": {k: old_state.get(k) for k in updates.keys()},
        "new_values": updates
    })
    
    write_wallets(wallets)
    return {
        "status": "success", 
        "wallet_id": payload.wallet_id,
        "updates": updates,
        "old_state": old_state,
        "new_state": wallet
    }
# --- Governance Approval Gateway Endpoints ---

@app.get("/api/admin/governance/requests")
def admin_list_governance_requests(x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch pending machine actions requiring human approval."""
    _verify_auth(x_sentinel_token)
    return {"requests": list(approval_manager.list_pending().values())}

class GovernanceResolveRequest(BaseModel):
    request_id: str
    decision: str # APPROVE or DENY
    actor_id: str
    notes: str = ""

@app.post("/api/admin/governance/resolve")
def admin_resolve_governance_route(payload: GovernanceResolveRequest, x_sentinel_token: Optional[str] = Header(default=None)):
    """Human decision on a pending agent action."""
    _verify_auth(x_sentinel_token)
    try:
        # Map Decision to status
        status = "approved" if payload.decision.upper() == "APPROVE" else "rejected"
        res = approval_manager.resolve_request(
            req_id=payload.request_id,
            status=status,
            actor_id=payload.actor_id,
            reason=payload.notes or "Admin Decision"
        )
        return {"status": "success", "resolved": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- New Oversight Console Endpoints ---

@app.get("/api/admin/analytics/spend")
def admin_get_spend_analytics(
    start_ts: float = 0.0, 
    end_ts: float = float('inf'),
    x_sentinel_token: Optional[str] = Header(default=None)
):
    """Aggregation endpoint for spend efficiency and project/agent metrics."""
    _verify_auth(x_sentinel_token)
    return analytics_aggregator.get_spend_operations_report(start_ts, end_ts)

@app.get("/api/admin/wallets/compliance")
def admin_get_compliance_wallets(x_sentinel_token: Optional[str] = Header(default=None)):
    """Filtered view of contractor wallets for compliance oversight."""
    _verify_auth(x_sentinel_token)
    all_wallets = read_wallets()
    contractors = {
        wid: w for wid, w in all_wallets.items() 
        if w.get("wallet_type") == "contractor"
    }
    return {"contractors": contractors}

@app.get("/api/admin/governance/history")
def admin_get_governance_history(limit: int = 100, x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch full history of governance decisions and expirations."""
    _verify_auth(x_sentinel_token)
    _verify_auth(x_sentinel_token)
    return {"history": approval_manager.list_all(limit=limit)}


@app.get("/api/admin/holds/active")
def admin_get_active_holds(x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch all active budget reservations and encumbrances."""
    _verify_auth(x_sentinel_token)
    # Using the approval_manager's integrated DB
    return {"holds": approval_manager.db.get_holds_by_status("active")}


@app.get("/api/admin/holds/history")
def admin_get_hold_history(limit: int = 100, x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch history of terminal hold states (settled/released/expired)."""
    _verify_auth(x_sentinel_token)
    from src.governance.db import SentinelDB
    db = SentinelDB()
    # Union of terminal states
    results = []
    for status in ["settled", "released", "expired"]:
        results.extend(db.get_holds_by_status(status, limit=limit))
    # Sort by created_at desc
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return {"history": results[:limit]}


@app.get("/api/admin/integrity/exceptions")
def admin_get_integrity_exceptions(x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch data on budget shortfalls and integrity violations."""
    _verify_auth(x_sentinel_token)
    from src.ledger.ledger import INTEGRITY_LOG, iter_accounting_events
    
    events = []
    # 1. Integrity Violations (State Machine failures)
    if INTEGRITY_LOG.exists():
        with open(INTEGRITY_LOG, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
                    
    # 2. Authoritative Budget Shortfalls from Ledger
    for event in iter_accounting_events():
        if event.get("event_type") == "budget_shortfall":
            events.append(event)
            
    # Sort by timestamp desc
    events.sort(key=lambda x: x.get("timestamp", x.get("_written_at", "")), reverse=True)
    return {"events": events}


@app.post("/api/admin/holds/{hold_id}/resolve")
def admin_resolve_hold(
    hold_id: str, 
    resolution_mode: str = Query(...), 
    audit_reason: str = Query(...),
    operator_id: str = Query("admin"),
    x_sentinel_token: Optional[str] = Header(default=None)
):
    """Authoritatively resolve a clamped hold (failed_shortfall)."""
    _verify_auth(x_sentinel_token)
    from src.ledger.holds import HoldManager
    hm = HoldManager()
    
    # We need the wallet_id for the hold
    hold_record = hm.db.get_hold(hold_id)
    if not hold_record:
        raise HTTPException(status_code=404, detail="Hold not found")
        
    wallet_id = hold_record["wallet_id"]
    
    success = hm.resolve_clamped_hold(
        hold_id=hold_id,
        wallet_id=wallet_id,
        resolution_mode=resolution_mode,
        audit_reason=audit_reason,
        operator_id=operator_id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve hold. Check mode compatibility.")
        
    return {"status": "success", "hold_id": hold_id, "mode": resolution_mode}


@app.get("/api/admin/analytics/spend")
def admin_get_spend_analytics(x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch current spend summary for all budget nodes."""
    _verify_auth(x_sentinel_token)
    return analytics_aggregator.get_current_spend_summary()


@app.get("/api/admin/analytics/governance")
def admin_get_governance_analytics(x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch pilot governance KPIs (human save rate, overrides, etc)."""
    _verify_auth(x_sentinel_token)
    return analytics_aggregator.get_governance_report()


@app.get("/api/admin/wallets/hierarchy")
def admin_get_wallet_hierarchy(x_sentinel_token: Optional[str] = Header(default=None)):
    """Fetch structured Org -> Project -> Agent hierarchy with anomaly flagging."""
    _verify_auth(x_sentinel_token)
    from src.ledger.ledger import read_wallets
    from src.ledger.holds import HoldManager
    
    wallets = read_wallets()
    hm = HoldManager()
    
    # 1. Fetch all clamped holds to identify 'flagged' wallets
    clamped_holds = hm.db.get_holds_by_status("failed_shortfall")
    flagged_wallets = {h["wallet_id"] for h in clamped_holds}
    
    # 2. Group by parent
    hierarchy = {} # parent_id -> list of children
    roots = []
    
    for w_id, w_data in wallets.items():
        parent = w_data.get("parent_wallet_id")
        if not parent:
            roots.append(w_id)
        else:
            if parent not in hierarchy:
                hierarchy[parent] = []
            hierarchy[parent].append(w_id)
            
    def _build_node(w_id):
        data = wallets[w_id]
        children_nodes = [_build_node(child) for child in hierarchy.get(w_id, [])]
        
        # A node is flagged if itself or any child has failed_shortfall holds
        is_flagged = w_id in flagged_wallets or any(c["is_flagged"] for c in children_nodes)
        
        return {
            "id": w_id,
            "name": data.get("name", w_id),
            "balance_jul": data.get("balance_jul", 0.0),
            "held_jul": data.get("held_jul", 0.0),
            "available_jul": round(data.get("balance_jul", 0.0) - data.get("held_jul", 0.0), 6),
            "is_flagged": is_flagged,
            "children": children_nodes
        }
        
    return {"hierarchy": [_build_node(root) for root in roots]}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SENTINEL_PORT", "8765"))
    host = os.getenv("SENTINEL_HOST", "127.0.0.1").strip() or "127.0.0.1"
    print(f"🛡️  Starting Sentinel Security Gateway on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
