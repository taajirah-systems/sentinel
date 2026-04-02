from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from src.ledger.ledger import Ledger
from src.ledger.accounting import AccountingEvent

class SettlementService:
    """
    Handles internal credit settlement to real-world value (ZAR).
    Enforces 'Contractor-only' payout restrictions.
    """
    def __init__(self, data_dir: str = "data"):
        self.ledger = Ledger(data_dir)
        # In a real scenario, this would check a database of verified contractors
        self.verified_contractors = {"taajirah-admin", "sentinel-dev-01"}

    def request_payout(self, actor_id: str, amount_jul: float, target_currency: str = "ZAR") -> Dict[str, Any]:
        """
        Processes a payout request from JOULE to ZAR.
        1 JUL = 1 ZAR.
        """
        if actor_id not in self.verified_contractors:
            return {
                "success": False,
                "reason": f"Actor {actor_id} is not a verified contractor. Payouts restricted."
            }

        # Record the settlement event in the ledger
        event = AccountingEvent(
            event_type="settlement",
            actor_id=actor_id,
            amount=amount_jul,
            credit_type="internal",
            purpose=f"Payout to {target_currency}",
            metadata={"status": "processed", "target_currency": target_currency}
        )
        self.ledger.log_event(event)
        
        return {
            "success": True,
            "amount_zar": amount_jul,
            "actor_id": actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_pending_settlements(self) -> List[Dict[str, Any]]:
        """Returns all settlement events for audit."""
        events = self.ledger.read_events()
        return [e for e in events if e.get("event_type") == "settlement"]
