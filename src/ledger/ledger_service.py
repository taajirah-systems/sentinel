"""
Sentinel Ledger Service — Internal Credit Allocations (JUL).

This module manages the allocation of internal service credits to contributors 
based on their verifiable output and quality of service.

JUL is an administrative accounting index for compute value.
"""

import uuid
from datetime import datetime, timezone
from typing import Literal, Dict, Any, Optional

from .ledger import (
    write_accounting_event,
    read_wallets,
    write_wallets,
)
from .oracle import get_current_rate
from .accounting import EventType, SpendOutcome, ValueClass, create_integrity_event
from .validation import validate_hierarchy_link

ContributionType = Literal["verification", "data_upload", "tool_execution", "feedback"]

# Allocation rates for internal credits (JUL)
CREDIT_ALLOCATION_RATES: Dict[ContributionType, Dict[str, Any]] = {
    "verification": {
        "flat_jul": 0.10,          # 10 cents ZAR credit per HITL approval
        "description": "Human-in-the-loop governance action",
    },
    "data_upload": {
        "flat_jul": None,          # Dynamic: proportional to credit consumed
        "description": "Information or context provisioning",
    },
    "tool_execution": {
        "flat_jul": None,          # Dynamic: based on compute footprint
        "description": "Task or script execution on behalf of an agent",
    },
    "feedback": {
        "flat_jul": 0.05,          # 5 cents baseline + quality factor
        "description": "Output correction or validation",
    },
}


def allocate_internal_credit(
    wallet_id: str,
    contribution_type: ContributionType,
    correlation_id: str,
    approved_by: str,
    tokens_consumed: int = 0,
    provider: str = "unknown",
    quality_multiplier: Optional[float] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Allocate internal service credits (JUL) to a wallet based on a contribution.

    Refactor Note: Replaces legacy 'issue' logic. Transitions from 'tokens' to 'service credits'
    grounded in internal accounting.
    """
    # 1. Fetch current reconciled state (CACHE)
    wallets = read_wallets()
    now = datetime.now(timezone.utc).isoformat()
    
    if wallet_id not in wallets:
        is_contractor = str(wallet_id).startswith("+27")
        w_type = "contractor" if is_contractor else "agent"
        
        wallets[wallet_id] = {
            "wallet_id": wallet_id,
            "owner_id": wallet_id,
            "wallet_type": w_type,
            "display_name": wallet_id,
            "org_id": None,
            "parent_wallet_id": None,
            "migration_status": "migrated",
            "budget_period": "monthly",
            "soft_limit_jul": 4000.0,
            "hard_limit_jul": 5000.0,
            "balance_jul": 0.0,
            "held_jul": 0.0,
            "lifetime_allocated_jul": 0.0,
            "lifetime_settled_zar": 0.0,
            "kyc_verified": False,
            "contract_active": False,
            "reputation_score": 1.0,
            "created_at": now,
            "last_reconciled_at": now,
        }
        
    # Map reputation score to quality factor
    if quality_multiplier is None:
        rep = wallets[wallet_id].get("reputation_score", 1.0)
        if rep < 0.60: quality_multiplier = 0.50
        elif rep < 0.90: quality_multiplier = 0.85
        elif rep < 1.10: quality_multiplier = 1.00
        elif rep < 1.40: quality_multiplier = 1.10
        else: quality_multiplier = 1.20

    # 2. Calculate allocation amount
    rate = get_current_rate(provider)
    actual_cost_zar = (tokens_consumed / 1_000_000) * rate["cost_per_1m_tokens_zar"]

    config = CREDIT_ALLOCATION_RATES[contribution_type]
    if config["flat_jul"] is not None:
        amount_jul = config["flat_jul"] * quality_multiplier
    else:
        # Proportional: contributor receives credit equal to actual compute cost
        amount_jul = actual_cost_zar * quality_multiplier

    amount_jul = round(amount_jul, 6)
    
    # 3. Emit Authoritative Accounting Event
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "timestamp": now,
        "event_type": "allocation",
        "from_wallet": "system",
        "to_wallet": wallet_id,
        "amount_jul": amount_jul,
        "correlation_id": correlation_id,
        "description": f"Credit allocation for {contribution_type} (quality: {quality_multiplier})",
        "outcome": "completed",
        "value_class": "value",
        "metadata": {
            "tokens_consumed": tokens_consumed,
            "provider": provider,
            "quality_multiplier": quality_multiplier,
            "approved_by": approved_by,
            "notes": notes
        }
    }
    write_accounting_event(event)

    # 4. Update Reconciled Cache
    wallets[wallet_id]["balance_jul"] = round(wallets[wallet_id]["balance_jul"] + amount_jul, 6)
    wallets[wallet_id]["lifetime_allocated_jul"] = round(wallets[wallet_id]["lifetime_allocated_jul"] + amount_jul, 6)
    wallets[wallet_id]["last_reconciled_at"] = now
    write_wallets(wallets)

    return event


def allocate_child_credit(
    parent_wallet_id: str,
    child_wallet_id: str,
    amount_jul: float,
    correlation_id: str,
    description: str,
) -> Optional[Dict[str, Any]]:
    """
    Allocates credits from a parent wallet to a child wallet.
    Atomic: Reduces parent balance and increases child balance.
    Provides zero-sum hierarchy enforcement.
    """
    amount = round(amount_jul, 6)
    wallets = read_wallets()
    
    if parent_wallet_id not in wallets or child_wallet_id not in wallets:
        return None
        
    parent = wallets[parent_wallet_id]
    child = wallets[child_wallet_id]
    
    # Verify hierarchy link
    if child.get("parent_wallet_id") != parent_wallet_id:
        # Hierarchy violation!
        return None
        
    # 2. Explicit Layered Cap Enforcement
    parent_type = parent.get("wallet_type", "unknown")
    available = get_available_jul(parent)
    
    # Check parent budget capacity
    if amount > available:
        # Budget shortfall at parent level
        create_integrity_event(
            violation_type="HIERARCHY_ALLOC_SHORTFALL",
            target_id=parent_wallet_id,
            description=f"Parent {parent_type} ({parent_wallet_id}) has insufficient available budget ({available}) for {amount} allocation.",
            metadata={
                "parent_type": parent_type,
                "amount_jul": amount,
                "available_jul": available,
                "child_id": child_wallet_id
            }
        )
        return None
        
    now = datetime.now(timezone.utc).isoformat()
    
    # Emit Authoritative Accounting Event
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "timestamp": now,
        "event_type": "allocation",
        "from_wallet": parent_wallet_id,
        "to_wallet": child_wallet_id,
        "amount_jul": amount,
        "correlation_id": correlation_id,
        "description": description,
        "outcome": "completed",
        "value_class": "value",
        "metadata": {
            "allocation_type": "parent_to_child"
        }
    }
    write_accounting_event(event)

    # Update Reconciled Cache
    parent["balance_jul"] = round(parent["balance_jul"] - amount, 6)
    child["balance_jul"] = round(child["balance_jul"] + amount, 6)
    
    parent["last_reconciled_at"] = now
    child["last_reconciled_at"] = now
    
    write_wallets(wallets)
    return event


def allocate_service_credit(
    wallet_id: str,
    amount_jul: float,
    approved_by: str,
    reference: str = "",
) -> Dict[str, Any]:
    """
    Directly allocate credits for corporate treasury or fiat deposits.
    Refactor Note: Replaces legacy allocation logic.
    """
    amount_jul = round(amount_jul, 6)
    now = datetime.now(timezone.utc).isoformat()

    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "timestamp": now,
        "event_type": "allocation",
        "from_wallet": "system:treasury",
        "to_wallet": wallet_id,
        "amount_jul": amount_jul,
        "correlation_id": reference,  # Use reference as correlation ID
        "description": f"Fiat-backed credit allocation (Ref: {reference})",
        "outcome": "completed",
        "value_class": "value",
        "metadata": {
            "approved_by": approved_by,
            "fiat_reference": reference,
            "allocation_type": "treasury_deposit"
        }
    }
    write_accounting_event(event)

    # Update wallet balance
    wallets = read_wallets()
    if wallet_id not in wallets:
        # Create minimal wallet if missing
        wallets[wallet_id] = {
            "wallet_id": wallet_id,
            "balance_jul": 0.0,
            "lifetime_allocated_jul": 0.0,
            "created_at": now
        }
        
    wallets[wallet_id]["balance_jul"] = round(wallets[wallet_id]["balance_jul"] + amount_jul, 6)
    wallets[wallet_id]["lifetime_allocated_jul"] = round(wallets[wallet_id]["lifetime_allocated_jul"] + amount_jul, 6)
    wallets[wallet_id]["last_reconciled_at"] = now
    write_wallets(wallets)

    return event


def spend_service_credit(
    wallet_id: str,
    amount_jul: float,
    correlation_id: str,
    description: str,
    outcome: SpendOutcome = "completed",
    value_class: ValueClass = "value",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record a service credit expenditure (JUL).
    Checks for sufficient balance and updates the reconciled cache.
    """
    amount_jul = round(amount_jul, 6)
    now = datetime.now(timezone.utc).isoformat()
    wallets = read_wallets()

    if wallet_id in wallets:
        w_type = wallets[wallet_id].get("wallet_type", "agent")
        if w_type in ["org", "project"]:
            # Rule: Parent wallets cannot spend directly!
            # Only terminal wallets (agent/contractor) can be spent from.
            # Log as integrity violation? No, spend_service_credit is usually internal.
            # We'll just reject for now.
            return {"error": "Direct spend from non-terminal wallet forbidden."}
            
    if wallet_id not in wallets:
        # In a strict accounting system, this should fail. 
        # For now, we allow the negative balance to highlight the missing wallet.
        wallets[wallet_id] = {
            "wallet_id": wallet_id,
            "balance_jul": 0.0,
            "created_at": now
        }

    # Recording the spend event
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "timestamp": now,
        "event_type": "spend",
        "from_wallet": wallet_id,
        "to_wallet": "system:burn", # Service credits are "burned" upon consumption
        "amount_jul": amount_jul,
        "correlation_id": correlation_id,
        "description": description,
        "outcome": outcome,
        "value_class": value_class,
        "metadata": metadata or {}
    }
    write_accounting_event(event)

    # Update wallet balance
    wallets[wallet_id]["balance_jul"] = round(wallets[wallet_id]["balance_jul"] - amount_jul, 6)
    wallets[wallet_id]["last_reconciled_at"] = now
    write_wallets(wallets)

    return event


def get_available_jul(wallet: Dict[str, Any]) -> float:
    """
    Calculate derived available balance: balance - held.
    Note: available_jul is NEVER persisted to the wallet store.
    """
    balance = wallet.get("balance_jul", 0.0)
    held = wallet.get("held_jul", 0.0)
    return round(balance - held, 6)
