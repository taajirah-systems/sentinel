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

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import the Sentinel runtime
from src.sentinel.main import SentinelRuntime, AuditDecision
from src.sentinel.approvals import ApprovalManager, PendingRequest
from src.sentinel.logger import audit_logger
from src.sentinel.redactor import redactor
from src.sentinel.inference_broker import inference_broker

app = FastAPI(
    title="Sentinel Security Gateway",
    description="HTTP API for command auditing with deterministic + LLM semantic analysis",
    version="2.0.0",
)


def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("SENTINEL_ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost", "http://127.0.0.1"]


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


class AuditRequest(BaseModel):
    """Request body for command auditing."""
    command: str


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
                rule_name="Policy Review", # We could extract this if we parsed the reason
                reason=result.get("reason", "Requires approval")
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

    # 1. Extract Prompt for Auditing
    # We audit the full conversation or just the last user message?
    # For now, let's audit the entire context joined by newlines.
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
def approve_request(request_id: str, x_sentinel_token: Optional[str] = Header(default=None)):
    """Approve and execute a pending request."""
    _verify_auth(x_sentinel_token)
    
    req = approval_manager.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")
    
    print(f"✅ Approving request {request_id}: {req.command}")
    
    # Execute with policy bypass
    try:
        if runtime is None:
             raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")
             
        result = runtime.run_intercepted_command(req.command, bypass_policy=True)
        approval_manager.resolve_request(request_id, "approved")
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


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SENTINEL_PORT", "8765"))
    host = os.getenv("SENTINEL_HOST", "127.0.0.1").strip() or "127.0.0.1"
    print(f"🛡️  Starting Sentinel Security Gateway on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
