import uuid
import time
from typing import Dict, Optional, Any
from pydantic import BaseModel

class PendingRequest(BaseModel):
    id: str
    command: str
    timestamp: float
    rule_name: str
    reason: str
    status: str = "pending" # pending, approved, rejected

class ApprovalManager:
    def __init__(self):
        self._requests: Dict[str, PendingRequest] = {}

    def create_request(self, command: str, rule_name: str, reason: str) -> str:
        req_id = str(uuid.uuid4())[:8] # Short ID for easier typing
        request = PendingRequest(
            id=req_id,
            command=command,
            timestamp=time.time(),
            rule_name=rule_name,
            reason=reason
        )
        self._requests[req_id] = request
        return req_id

    def get_request(self, req_id: str) -> Optional[PendingRequest]:
        return self._requests.get(req_id)

    def list_pending(self) -> Dict[str, PendingRequest]:
        return {k: v for k, v in self._requests.items() if v.status == "pending"}

    def resolve_request(self, req_id: str, status: str) -> bool:
        if req_id in self._requests:
            self._requests[req_id].status = status
            return True
        return False
    
    def cleanup_old_requests(self, max_age_seconds: int = 3600):
        # Optional: cleanup logic
        pass
