"""
Sentinel Hold Manager — Escrow-style credit reservation logic.
"""

import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from .ledger import read_wallets, write_wallets, iter_accounting_events
from .accounting import create_accounting_event, create_integrity_event
from .ledger_service import get_available_jul
from ..governance.db import SentinelDB

class HoldManager:
    """
    Manages the lifecycle of a budget hold: reservation, settlement, and release.
    
    Allowed Transitions:
    - active -> settled             (Final spend within budget or absorbed variance)
    - active -> released            (Manual release or rejection; funds returned)
    - active -> expired             (Automated inactivity cleanup; funds returned)
    - active -> failed_shortfall    (Terminal: actual > estimated + available. Funds remain CLAMPED for review.)
    
    Note: 'failed_shortfall' is a terminal state. Held funds are NOT auto-released to 
    prevent further spend until manual reconciliation. Retries require a new request.
    """
    def __init__(self, db_path: str = "data/sentinel.db"):
        self.db = SentinelDB(db_path)

    def create_hold(
        self, 
        wallet_id: str, 
        amount_jul: float, 
        correlation_id: str,
        description: str,
        project_id: str,
        org_id: str,
        expires_at: Optional[str] = None
    ) -> Optional[str]:
        """
        Reserves credits by moving them from 'available' to 'held'.
        Returns hold_id if successful, None otherwise.
        """
        wallets = read_wallets()
        if wallet_id not in wallets:
            return None
        
        wallet = wallets[wallet_id]
        amount = round(amount_jul, 6)
        
        # 1. Check Hard Limit vs Available
        available = get_available_jul(wallet)
        if amount > available:
            # Check hard limit check (No Overdraft Policy)
            return None
            
        # 2. Update Persisted State
        hold_id = f"hold_{uuid.uuid4().hex[:16]}"
        wallet["held_jul"] = round(wallet.get("held_jul", 0.0) + amount, 6)
        
        # 3. Emit hold_created event
        create_accounting_event(
            event_type="hold_created",
            from_wallet=wallet_id,
            to_wallet="system:escrow",
            amount_jul=amount,
            description=description,
            correlation_id=correlation_id,
            metadata={
                "hold_id": hold_id,
                "project_id": project_id,
                "org_id": org_id,
                "expires_at": expires_at
            }
        )
        
        write_wallets(wallets)
        
        # 4. Update State Cache (SentinelDB)
        # Parse expires_at if it's a string timestamp
        expires_ts = None
        if expires_at:
            try:
                # Assuming ISO format from metadata or float timestamp
                expires_ts = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc).timestamp()
            except (ValueError, TypeError):
                try:
                    expires_ts = float(expires_at)
                except (ValueError, TypeError):
                    pass

        self.db.insert_hold(
            hold_id=hold_id, 
            request_id=correlation_id, 
            wallet_id=wallet_id, 
            amount_jul=amount,
            project_id=project_id,
            org_id=org_id,
            expires_at=expires_ts
        )
        
        return hold_id

    def settle_hold(
        self,
        hold_id: str,
        wallet_id: str,
        actual_amount_jul: float,
        estimated_amount_jul: float,
        description: str,
        correlation_id: str
    ) -> bool:
        """
        Consumes actual spend from held credits and releases surplus.
        """
        wallets = read_wallets()
        if wallet_id not in wallets:
            return False
            
        wallet = wallets[wallet_id]
        actual = round(actual_amount_jul, 6)
        estimated = round(estimated_amount_jul, 6)
        
        # 1. Verification of state (State Machine)
        hold_record = self.db.get_hold(hold_id)
        if not hold_record:
            create_integrity_event(
                violation_type="HOLD_NOT_FOUND",
                target_id=hold_id,
                description=f"Attempted to settle unknown hold {hold_id}"
            )
            return False
            
        current_status = hold_record.get("status")
        if current_status != "active":
            create_integrity_event(
                violation_type="INVALID_STATE_TRANSITION",
                target_id=hold_id,
                description=f"Attempted to settle hold in {current_status} state",
                metadata={"attempted_transition": f"{current_status} -> settled"}
            )
            return False

        if wallet.get("held_jul", 0.0) < estimated:
            # Integrity error: wallet doesn't have the estimated amount held
            create_integrity_event(
                violation_type="BUDGET_INCONSISTENCY",
                target_id=hold_id,
                description=f"Wallet {wallet_id} held_jul ({wallet.get('held_jul')}) < estimated ({estimated})",
                metadata={"wallet_id": wallet_id, "hold_id": hold_id}
            )
            return False
            
        # 2. Settlement Logic
        surplus = round(max(0, estimated - actual), 6)
        shortfall = round(max(0, actual - estimated), 6)
        
        available = get_available_jul(wallet)
        
        # FAIL CLOSED if shortfall exists and cannot be absorbed by available budget
        if shortfall > 0 and shortfall > available:
            create_accounting_event(
                event_type="budget_shortfall",
                from_wallet=wallet_id,
                to_wallet="system:burn",
                amount_jul=shortfall,
                description=f"Under-estimation shortfall ({shortfall}) exceeded available budget for {hold_id}",
                correlation_id=correlation_id,
                metadata={
                    "estimated_amount_jul": estimated,
                    "actual_amount_jul": actual,
                    "available_jul": available,
                    "hold_id": hold_id,
                    "reason": "INSUFFICIENT_BUDGET_FOR_SHORTFALL"
                }
            )
            # Mark hold as failed due to shortfall
            self.db.update_hold_status(
                hold_id, 
                "failed_shortfall", 
                resolved_at=time.time(),
                status_reason=f"Shortfall {shortfall} blocked by cap enforcement."
            )
            return False

        # 3. Commit Financial Changes
        # Reducing held by the FULL estimated amount
        wallet["held_jul"] = round(wallet["held_jul"] - estimated, 6)
        # Reducing balance by the ACTUAL amount
        wallet["balance_jul"] = round(wallet["balance_jul"] - actual, 6)
        
        # 4. Emit hold_settled event
        now_ts = time.time()
        create_accounting_event(
            event_type="hold_settled",
            from_wallet=wallet_id,
            to_wallet="system:burn",
            amount_jul=actual,
            description=description,
            correlation_id=correlation_id,
            metadata={
                "hold_id": hold_id,
                "actual_amount_jul": actual,
                "estimated_amount_jul": estimated,
                "surplus_released_jul": surplus,
                "shortfall_drawn_jul": shortfall,
                "settled_at": datetime.fromtimestamp(now_ts, timezone.utc).isoformat()
            }
        )
        
        write_wallets(wallets)
        
        # 5. Update State Cache (SentinelDB)
        self.db.update_hold_status(
            hold_id, 
            "settled", 
            resolved_at=now_ts,
            actual_amount_jul=actual,
            surplus_released_jul=surplus
        )
        
        return True

    def release_hold(
        self,
        hold_id: str,
        wallet_id: str,
        amount_jul: float,
        reason: str,
        correlation_id: str,
        is_expiry: bool = False
    ) -> bool:
        """
        Returns reserved credits to 'available' pool.
        Used for rejections or expirations.
        """
        wallets = read_wallets()
        if wallet_id not in wallets:
            return False
            
        wallet = wallets[wallet_id]
        amount = round(amount_jul, 6)
        
        # 1. Verification of state (State Machine)
        hold_record = self.db.get_hold(hold_id)
        if not hold_record:
            # This might be valid for legacy holds not in the DB, 
            # but for a high-integrity system, everything must be tracked.
            # In Phase 4, we would expect a record.
            create_integrity_event(
                violation_type="HOLD_NOT_FOUND",
                target_id=hold_id,
                description=f"Attempted to release unknown hold {hold_id}"
            )
            return False

        current_status = hold_record.get("status")
        if current_status != "active":
            create_integrity_event(
                violation_type="INVALID_STATE_TRANSITION",
                target_id=hold_id,
                description=f"Attempted to release hold in {current_status} state",
                metadata={"attempted_transition": f"{current_status} -> released"}
            )
            return False

        if wallet.get("held_jul", 0.0) < amount:
            create_integrity_event(
                violation_type="BUDGET_INCONSISTENCY",
                target_id=hold_id,
                description=f"Wallet {wallet_id} held_jul ({wallet.get('held_jul')}) < amount ({amount})",
                metadata={"wallet_id": wallet_id, "hold_id": hold_id}
            )
            return False
            
        wallet["held_jul"] = round(wallet["held_jul"] - amount, 6)
        
        event_type = "hold_expired" if is_expiry else "hold_released"
        create_accounting_event(
            event_type=event_type,
            from_wallet="system:escrow",
            to_wallet=wallet_id,
            amount_jul=amount,
            description=reason,
            correlation_id=correlation_id,
            metadata={
                "hold_id": hold_id,
                "released_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        write_wallets(wallets)
        
        # 4. Update State Cache (SentinelDB)
        status = "expired" if is_expiry else "released"
        self.db.update_hold_status(
            hold_id, 
            status, 
            resolved_at=time.time(),
            status_reason=reason
        )
        
        return True

    def resolve_clamped_hold(
        self,
        hold_id: str,
        wallet_id: str,
        resolution_mode: str,
        audit_reason: str,
        operator_id: str
    ) -> bool:
        """
        Authoritatively resolves a hold in 'failed_shortfall' state.
        Modes:
        - release: Funds remain with wallet (available_jul increases).
        - fund_and_settle: Funds are burned (settled); shortfall is ignored/absorbed.
        - force_settle: Funds are burned (settled); uses exact held amount.
        """
        # 1. Validation
        hold_record = self.db.get_hold(hold_id)
        if not hold_record:
            return False
            
        previous_state = hold_record.get("status")
        if previous_state != "failed_shortfall":
            create_integrity_event(
                violation_type="INVALID_RESOLUTION_ATTEMPT",
                target_id=hold_id,
                description=f"Only 'failed_shortfall' holds can be resolve-overridden (current: {previous_state}).",
                metadata={"hold_id": hold_id, "status": previous_state}
            )
            return False
            
        # 2. Extract Base Data
        estimated = hold_record["amount_jul"]
        correlation_id = f"res_{hold_id}"
        ts = time.time()
        
        # 3. Apply Action (Bypassing Standard Guards for Pilot-Safe Operator Override)
        wallets = read_wallets()
        wallet = wallets[wallet_id]
        new_state = "unknown"
        
        # Standard Audit Metadata (Mandatory 7-field)
        audit_metadata = {
            "actor_id": operator_id,
            "reason": audit_reason,
            "previous_state": previous_state,
            "hold_id": hold_id,
            "correlation_id": correlation_id,
            "timestamp": ts,
            "override_mode": resolution_mode
        }
        
        if resolution_mode == "release":
            new_state = "released"
            wallet["held_jul"] = round(max(0, wallet.get("held_jul", 0.0) - estimated), 6)
            create_accounting_event(
                event_type="hold_manually_released",
                from_wallet="system:escrow",
                to_wallet=wallet_id,
                amount_jul=0.0,
                description=f"Pilot-Safe Release: {audit_reason}",
                correlation_id=correlation_id,
                metadata={**audit_metadata, "new_state": new_state}
            )
            write_wallets(wallets)
            self.db.update_hold_status(hold_id, new_state, status_reason=audit_reason, resolved_at=ts)
            return True
            
        elif resolution_mode == "fund_and_settle":
            new_state = "settled"
            # In 'fund_and_settle', we settle the original estimation, effectively forcing the shortfall closure.
            # (In more complex versions, this would consume also from available if actual > estimated,
            # but for this pilot-safe bypass, we assume the Operator settles for exactly the held amount.)
            wallet["held_jul"] = round(max(0, wallet.get("held_jul", 0.0) - estimated), 6)
            wallet["balance_jul"] = round(wallet["balance_jul"] - estimated, 6)
            
            create_accounting_event(
                event_type="hold_manually_settled_with_funding",
                from_wallet=wallet_id,
                to_wallet="system:burn",
                amount_jul=estimated,
                description=f"Pilot-Safe Fund & Settle: {audit_reason}",
                correlation_id=correlation_id,
                metadata={**audit_metadata, "new_state": new_state}
            )
            write_wallets(wallets)
            self.db.update_hold_status(hold_id, new_state, status_reason=audit_reason, resolved_at=ts)
            return True

        elif resolution_mode == "force_settle":
            new_state = "settled"
            wallet["held_jul"] = round(max(0, wallet.get("held_jul", 0.0) - estimated), 6)
            wallet["balance_jul"] = round(wallet["balance_jul"] - estimated, 6)
            
            create_accounting_event(
                event_type="hold_manually_force_settled",
                from_wallet=wallet_id,
                to_wallet="system:burn",
                amount_jul=estimated,
                description=f"Pilot-Safe Force Settle: {audit_reason}",
                correlation_id=correlation_id,
                metadata={**audit_metadata, "new_state": new_state}
            )
            write_wallets(wallets)
            self.db.update_hold_status(hold_id, new_state, status_reason=audit_reason, resolved_at=ts)
            return True
            
        return False

    def reconcile_held_cache(self) -> Dict[str, float]:
        """
        Scans ALL accounting events to recalculate the authoritative 'held_jul' per wallet.
        Returns a mapping of wallet_id -> authoritative_held_jul.
        """
        held_authoritative = {}

        for event in iter_accounting_events():
            e_type = event.get("event_type")
            amount = round(event.get("amount_jul", 0.0), 6)
            
            # Identify the wallet ID for hold events
            # For created: from_wallet
            # For released/expired: to_wallet (returning to available)
            # For settled: from_wallet (the source of the original hold)
            w_id = event.get("from_wallet")
            if e_type in ["hold_released", "hold_expired"]:
                w_id = event.get("to_wallet")
            
            if not w_id or w_id.startswith("system:burn") or w_id == "system":
                continue
            
            if w_id not in held_authoritative:
                held_authoritative[w_id] = 0.0
                
            if e_type == "hold_created":
                held_authoritative[w_id] = round(held_authoritative[w_id] + amount, 6)
            elif e_type in ["hold_settled", "hold_released", "hold_expired"]:
                # Note: For hold_settled, we ALWAYS release the full ESTIMATED amount.
                est_amount = event.get("metadata", {}).get("estimated_amount_jul", amount)
                held_authoritative[w_id] = round(held_authoritative[w_id] - est_amount, 6)
                
        return {k: round(v, 6) for k, v in held_authoritative.items()}

    def repair_held_jul_cache(self):
        """
        Authoritatively repairs the wallets.json 'held_jul' field from the ledger history.
        """
        from .ledger import write_wallets # local import for safety
        authoritative = self.reconcile_held_cache()
        wallets = read_wallets()
        repaired_count = 0
        
        for w_id, auth_held in authoritative.items():
            if w_id in wallets:
                current_held = wallets[w_id].get("held_jul", 0.0)
                if abs(current_held - auth_held) > 0.000001:
                    wallets[w_id]["held_jul"] = auth_held
                    repaired_count += 1
        
        if repaired_count > 0:
            write_wallets(wallets)
            print(f"Reconciliation complete. Repaired {repaired_count} wallet caches.")
        else:
            print("Held cache is in sync with authoritative ledger.")
