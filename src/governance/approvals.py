import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from pydantic import BaseModel

# Import DB (delayed import to avoid circular dependency if needed, but here it's fine)
# We need to handle the import carefully. sentinel_db imports PendingRequest.
# So define PendingRequest first.

class PendingRequest(BaseModel):
    id: str
    wallet_id: str
    agent_id: str
    project_id: str = "default"
    command: str
    estimated_cost_jul: float = 0.0
    risk_score: int = 0
    status: str = "pending" # pending, approved, rejected
    rule_name: str
    reason: str             # Original trigger reason
    expires_at: float
    created_at: float
    resolved_at: Optional[float] = None
    actor_id: Optional[str] = None
    resolution_reason: Optional[str] = None
    hold_id: Optional[str] = None

class ApprovalManager:
    def __init__(self, db_path: str = "data/sentinel.db"):
        # Import inside to avoid circular dependency
        from .db import SentinelDB
        self.db = SentinelDB(db_path)

    def create_request(
        self, 
        command: str, 
        rule_name: str, 
        reason: str,
        wallet_id: str,
        agent_id: str,
        project_id: str = "default",
        org_id: str = "unknown",
        estimated_cost_jul: float = 0.0,
        risk_score: int = 0,
        ttl_seconds: int = 3600
    ) -> Optional[str]:
        # 1. Create Budget Hold (Mandatory)
        from src.ledger.holds import HoldManager
        hm = HoldManager()
        
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        now = time.time()
        expires_at_dt = datetime.fromtimestamp(now + ttl_seconds, tz=timezone.utc).isoformat()
        
        hold_id = hm.create_hold(
            wallet_id=wallet_id,
            amount_jul=estimated_cost_jul,
            correlation_id=req_id,
            description=f"Hold for request {req_id}: {command[:50]}...",
            project_id=project_id,
            org_id=org_id,
            expires_at=expires_at_dt
        )
        
        if not hold_id:
            # Insufficient Available Budget
            return None

        # 2. Persist Governance Request
        request = PendingRequest(
            id=req_id,
            wallet_id=wallet_id,
            agent_id=agent_id,
            project_id=project_id,
            command=command,
            estimated_cost_jul=estimated_cost_jul,
            risk_score=risk_score,
            rule_name=rule_name,
            reason=reason,
            expires_at=now + ttl_seconds,
            created_at=now,
            hold_id=hold_id
        )
        self.db.insert_approval(request)
        return req_id

    def get_request(self, req_id: str) -> Optional[PendingRequest]:
        return self.db.get_approval(req_id)

    def list_pending(self) -> Dict[str, PendingRequest]:
        return self.db.get_pending_approvals()

    def list_all(self, limit: int = 100) -> List[PendingRequest]:
        """Fetch full history of approval requests including resolution status."""
        return self.db.get_all_approvals(limit)

    def resolve_request(self, req_id: str, status: str, actor_id: str, reason: str, actual_cost_jul: Optional[float] = None) -> bool:
        """Resolve a pending request and its associated budget hold."""
        request = self.db.get_approval(req_id)
        if not request:
            return False
            
        # 1. Update Governance Status
        self.db.update_approval_status(req_id, status, actor_id=actor_id, resolution_reason=reason)
        
        # 2. Reconcile Budget Hold
        if request.hold_id:
            from src.ledger.holds import HoldManager
            hm = HoldManager()
            
            if status == "approved":
                # Final settlement
                cost = actual_cost_jul if actual_cost_jul is not None else request.estimated_cost_jul
                hm.settle_hold(
                    hold_id=request.hold_id,
                    wallet_id=request.wallet_id,
                    actual_amount_jul=cost,
                    estimated_amount_jul=request.estimated_cost_jul,
                    description=f"Settlement for {req_id}: {reason}",
                    correlation_id=req_id
                )
            else:
                # Release/Void
                hm.release_hold(
                    hold_id=request.hold_id,
                    wallet_id=request.wallet_id,
                    amount_jul=request.estimated_cost_jul,
                    reason=f"Release for {req_id}: {status} - {reason}",
                    correlation_id=req_id,
                    is_expiry=(status == "expired")
                )
        return True
    
    def cleanup_old_requests(self):
        """Purge expired requests and release associated budget holds."""
        now = time.time()
        expired_ids = self.db.get_expired_ids(now)
        
        if not expired_ids:
            return
            
        for req_id in expired_ids:
            # We resolve them as expired one by one to trigger the hold release logic
            self.resolve_request(
                req_id=req_id,
                status="expired",
                actor_id="system:governance",
                reason="TTL exceeded without resolution"
            )
            
            from src.ledger.ledger import write_compliance_event
            write_compliance_event({
                "event_type": "governance_expiry",
                "request_id": req_id,
                "status": "expired",
                "reason": "TTL exceeded without resolution",
                "timestamp": now
            })
