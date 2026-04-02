"""
Sentinel Accounting — Core logic for credit allocation and spend outcomes.

This module defines the business rules for how service credits (JUL) move 
between wallets and how their status is classified.
"""

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional, Dict, Any

from .ledger import (
    write_accounting_event, 
    write_integrity_event,
    read_wallets, 
    write_wallets
)

# Enumerations for strict classification
WalletType = Literal["agent", "project", "client", "contractor", "treasury", "system"]
BudgetPeriod = Literal["daily", "weekly", "monthly", "project_lifetime"]
SpendOutcome = Literal["completed", "blocked", "corrected", "failed", "pending_approval", "abandoned"]
ValueClass = Literal["value", "waste", "uncertain", "review_required"]
EventType = Literal[
    "allocation", 
    "spend", 
    "deposit", 
    "settlement", 
    "hold_created", 
    "hold_settled", 
    "hold_released", 
    "hold_expired",
    "budget_shortfall"
]

def create_accounting_event(
    event_type: EventType,
    from_wallet: str,
    to_wallet: str,
    amount_jul: float,
    description: str,
    correlation_id: str,
    outcome: Optional[SpendOutcome] = None,
    value_class: Optional[ValueClass] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create and record an authoritative accounting event.
    """
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "amount_jul": round(amount_jul, 6),
        "correlation_id": correlation_id,
        "description": description,
        "outcome": outcome,
        "value_class": value_class,
        "metadata": metadata or {}
    }
    
    write_accounting_event(event)
    return event

def create_integrity_event(
    violation_type: str,
    target_id: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create and record an authoritative integrity violation event.
    Used for failed state machine transitions or bypass attempts.
    """
    event = {
        "event_id": f"intg_{uuid.uuid4().hex[:16]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "violation_type": violation_type,
        "target_id": target_id,
        "description": description,
        "metadata": metadata or {}
    }
    
    write_integrity_event(event)
    return event

def reconcile_wallet_spend(
    wallet_id: str,
    amount_jul: float,
    event_type: Literal["spend", "hold", "release"],
    correlation_id: str
):
    """
    Update the derived wallet cache based on a spend/hold event.
    Note: In a full implementation, this would be a projection from the ledger.
    """
    wallets = read_wallets()
    if wallet_id not in wallets:
        return # Should ideally log a consistency error
        
    wallet = wallets[wallet_id]
    amount = round(amount_jul, 6)
    
    if event_type == "hold":
        wallet["balance_jul"] = round(wallet["balance_jul"] - amount, 6)
        wallet["held_jul"] = round(wallet.get("held_jul", 0.0) + amount, 6)
    elif event_type == "release":
        wallet["balance_jul"] = round(wallet["balance_jul"] + amount, 6)
        wallet["held_jul"] = round(wallet.get("held_jul", 0.0) - amount, 6)
    elif event_type == "spend":
        # If it was previously held, release the hold first
        # This logic will be refined in Phase 3
        wallet["balance_jul"] = round(wallet["balance_jul"] - amount, 6)
        
    wallet["last_reconciled_at"] = datetime.now(timezone.utc).isoformat()
    write_wallets(wallets)
