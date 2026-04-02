"""
Sentinel JOULE Wallet — Balance queries and fiat withdrawal requests.

Withdrawals are always pending until approved by a human via the dashboard.
"""

from datetime import datetime, timezone
import uuid

from .ledger import read_wallets, write_wallets, write_transaction, write_compliance_event
from .oracle import get_jul_to_zar

class ComplianceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def get_balance(recipient: str) -> dict:
    """
    Return the current JOULE balance and ZAR equivalent for a recipient.

    Returns:
        {
          "recipient": str,
          "balance_jul": float,
          "balance_zar_equiv": float,
          "lifetime_earned_jul": float,
          "lifetime_withdrawn_zar": float,
        }
    """
    wallets = read_wallets()
    if recipient not in wallets:
        return {
            "recipient": recipient,
            "balance_jul": 0.0,
            "balance_zar_equiv": 0.0,
            "lifetime_earned_jul": 0.0,
            "lifetime_withdrawn_zar": 0.0,
        }
    w = wallets[recipient]
    rate = get_jul_to_zar()
    return {
        "recipient": recipient,
        "balance_jul": w["balance_jul"],
        "balance_zar_equiv": round(w["balance_jul"] * rate, 2),
        "lifetime_earned_jul": w["lifetime_earned_jul"],
        "lifetime_withdrawn_zar": w["lifetime_withdrawn_zar"],
        "jul_to_zar_rate": rate,
    }


def request_withdrawal(
    recipient: str,
    amount_jul: float,
    payout_method: str,
    payout_ref: str,
    requested_by: str,
) -> dict:
    """
    Create a pending withdrawal request.

    All withdrawals are frozen until a human approves them via the dashboard.
    No funds move until approve_withdrawal() is called.

    Args:
        recipient:      Wallet identifier (phone number, etc.)
        amount_jul:     How many JOULE to withdraw.
        payout_method:  e.g. "bank_transfer", "payfast", "crypto"
        payout_ref:     Account number, PayFast email, crypto address, etc.
        requested_by:   Who initiated this request.

    Returns:
        The pending transaction record.
    """
    wallets = read_wallets()
    wallet_data = wallets.get(recipient, {})
    balance = wallet_data.get("balance_jul", 0.0)

    if amount_jul <= 0:
        raise ValueError("Withdrawal amount must be positive.")
    if amount_jul > balance:
        raise ValueError(f"Insufficient balance: {balance:.4f} JUL available.")

    rate = get_jul_to_zar()
    amount_zar = round(amount_jul * rate, 2)

    # A. Schema gate
    if "schema_version" not in wallet_data or "kyc_verified" not in wallet_data or "contract_active" not in wallet_data:
        raise ComplianceError("ERR_SCHEMA_MISSING_COMPLIANCE_FIELDS", "Wallet is missing strict compliance fields.")

    # B. Wallet type gate
    if wallet_data.get("wallet_type") != "contractor":
        raise ComplianceError("ERR_WALLET_TYPE_NOT_SETTLEMENT_ELIGIBLE", "Only 'contractor' wallets are eligible for fiat settlement.")

    # C. KYC gate
    if not wallet_data.get("kyc_verified"):
        raise ComplianceError("ERR_KYC_REQUIRED", "Recipient has not completed KYC compliance verification.")

    # D. Contract gate
    if not wallet_data.get("contract_active"):
        raise ComplianceError("ERR_CONTRACT_INACTIVE", "Recipient contract status is not active.")

    # E. Monthly cap gate
    monthly_limit = wallet_data.get("monthly_settlement_limit_zar", 5000.0)
    month_withdrawn = wallet_data.get("this_month_withdrawn_zar", 0.0)
    
    if (amount_zar + month_withdrawn) > monthly_limit:
        raise ComplianceError("ERR_MONTHLY_LIMIT_EXCEEDED", f"Request ({amount_zar} ZAR) limits ({monthly_limit} ZAR cap).")

    tx_id = f"tx_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Emit append-only compliance event for the settlement request
    write_compliance_event({
        "event_type": "settlement_requested",
        "timestamp": now,
        "actor_id": requested_by,
        "wallet_id": recipient,
        "reason": f"Requested {amount_zar} ZAR via {payout_method}",
        "correlation_id": tx_id
    })

    tx_record = {
        "id": tx_id,
        "type": "withdraw",
        "status": "pending_approval",      # ← HITL gate
        "from": recipient,
        "to": f"{payout_method}:{payout_ref}",
        "amount_jul": amount_jul,
        "amount_zar": amount_zar,
        "jul_to_zar_rate": rate,
        "requested_by": requested_by,
        "approved_by": None,
        "timestamp": now,
        "approved_at": None,
    }

    # Reserve the balance (deduct immediately, refund if rejected)
    wallets[recipient]["balance_jul"] = round(balance - amount_jul, 6)
    write_wallets(wallets)
    write_transaction(tx_record)

    print(
        f"[WALLET] Withdrawal request {tx_id}: "
        f"{amount_jul} JUL → {amount_zar} ZAR via {payout_method} "
        f"[PENDING APPROVAL]"
    )
    return tx_record


def approve_withdrawal(tx_id: str, approved_by: str) -> dict:
    """
    Approve a pending withdrawal. In production this triggers actual payout.
    For now it marks the record as approved and updates lifetime_withdrawn.

    Args:
        tx_id:       The transaction ID to approve.
        approved_by: Human identity authorising the payout.

    Returns:
        Updated transaction record.
    """
    from .ledger import TRANSACTION_LOG
    import json

    # Find the pending transaction
    records = []
    target = None
    with open(TRANSACTION_LOG, "r") as f:
        for line in f:
            r = json.loads(line)
            records.append(r)
            if r.get("id") == tx_id and r.get("status") == "pending_approval":
                target = r

    if not target:
        raise ValueError(f"No pending withdrawal found with id={tx_id}")

    now = datetime.now(timezone.utc).isoformat()
    target["status"] = "approved"
    target["approved_by"] = approved_by
    target["approved_at"] = now

    # Update lifetime_withdrawn in wallet
    wallets = read_wallets()
    recipient = target["from"]
    if recipient in wallets:
        wallets[recipient]["lifetime_withdrawn_zar"] = round(
            wallets[recipient].get("lifetime_withdrawn_zar", 0.0) + target["amount_zar"],
            2,
        )
        wallets[recipient]["this_month_withdrawn_zar"] = round(
            wallets[recipient].get("this_month_withdrawn_zar", 0.0) + target["amount_zar"],
            2,
        )
    write_wallets(wallets)

    # Emit compliance event for approval
    write_compliance_event({
        "event_type": "settlement_approved",
        "timestamp": now,
        "actor_id": approved_by,
        "wallet_id": recipient,
        "reason": f"Approved settlement of {target['amount_zar']} ZAR",
        "correlation_id": tx_id
    })

    # Append the approved record (audit log — we don't edit, we append)
    write_transaction({**target, "event": "approval_confirmed"})

    print(f"[WALLET] Withdrawal {tx_id} APPROVED by {approved_by} — {target['amount_zar']} ZAR")
    return target
