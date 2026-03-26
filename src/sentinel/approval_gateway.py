"""
Sentinel Approval Gateway
==========================
Provides a REQUIRE_APPROVAL flow for high-risk commands flagged as "review"
by the policy engine. The gateway:

  1. Emits an `approval_pending` JSONL event
  2. Prompts the operator for a decision (approve / deny)
  3. Captures actor ID and mandatory override reason
  4. Emits an `approval_logged` JSONL event with full provenance
  5. Returns the decision to the runtime

In automated environments, set SENTINEL_AUTO_DENY=1 to default to deny
without prompting. Set SENTINEL_OPERATOR_ID to identify the approving actor.

Usage (from main.py):
    from src.sentinel.approval_gateway import ApprovalGateway
    gw     = ApprovalGateway()
    result = gw.request_approval(cmd, correlation_id, rule_id, reason)
    if result["approved"]:
        # proceed with execution
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Import audit logger — reuse the existing structured logger
_THIS  = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS.parent.parent))
from src.sentinel.logger import AuditLogger

_logger = AuditLogger(log_path=str(_THIS / "logs" / "audit_structured.jsonl"))


class ApprovalGateway:
    """
    Operator approval gateway for REQUIRE_APPROVAL decisions.

    Environment variables:
      SENTINEL_OPERATOR_ID   — identifier of the approving operator
      SENTINEL_AUTO_DENY     — if "1", auto-deny without prompting (CI/CD safe)
    """

    def __init__(self):
        self.auto_deny   = os.environ.get("SENTINEL_AUTO_DENY", "0") == "1"
        self.operator_id = os.environ.get("SENTINEL_OPERATOR_ID", "unknown-operator")

    # ── Public API ────────────────────────────────────────────────────────────

    def request_approval(
        self,
        command: str,
        correlation_id: str,
        rule_id: str = "—",
        reason: str  = "Policy flagged command as high-risk",
        input_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request operator approval for a high-risk command.

        Returns:
            {"approved": bool, "actor_id": str, "override_reason": str}
        """
        input_str = input_str or command

        # ── 1. Emit approval_pending event ────────────────────────────────────
        _logger.log_event(
            event_type     = "approval_pending",
            stage          = "approval_pending",
            correlation_id = correlation_id,
            input_str      = input_str,
            decision       = "pending",
            reason         = reason,
            metadata       = {
                "rule_id":   rule_id,
                "command":   command,
                "auto_deny": self.auto_deny,
            },
        )

        # ── 2. Auto-deny path (CI/CD safe) ───────────────────────────────────
        if self.auto_deny:
            override_reason = "Auto-denied: SENTINEL_AUTO_DENY=1"
            self._emit_logged(
                correlation_id, input_str, command, rule_id,
                decision="deny", override_reason=override_reason
            )
            return {
                "approved":       False,
                "actor_id":       self.operator_id,
                "override_reason": override_reason,
            }

        # ── 3. Interactive prompt ─────────────────────────────────────────────
        print(f"\n{'═'*60}")
        print(f"  🔔  APPROVAL REQUIRED — Sentinel")
        print(f"{'═'*60}")
        print(f"  Command     : {command!r}")
        print(f"  Rule        : {rule_id}")
        print(f"  Reason      : {reason}")
        print(f"  Trace ID    : {correlation_id}")
        print(f"  Operator    : {self.operator_id}")
        print(f"{'─'*60}")

        # Mandatory override reason
        while True:
            try:
                override_reason = input("  Override reason (mandatory, cannot be empty): ").strip()
            except EOFError:
                override_reason = ""
            if override_reason:
                break
            print("  ⚠️  Override reason is required.")

        # Approve / deny
        while True:
            try:
                raw = input("  Decision [approve/deny]: ").strip().lower()
            except EOFError:
                raw = "deny"
            if raw in ("approve", "a", "yes", "y"):
                decision = "approve"
                break
            elif raw in ("deny", "d", "no", "n"):
                decision = "deny"
                break
            print("  Please enter 'approve' or 'deny'.")

        approved = decision == "approve"

        # ── 4. Emit approval_logged event ─────────────────────────────────────
        self._emit_logged(
            correlation_id, input_str, command, rule_id,
            decision=decision, override_reason=override_reason
        )

        print(f"  → Decision logged: {decision.upper()}  (actor: {self.operator_id})\n")

        return {
            "approved":        approved,
            "actor_id":        self.operator_id,
            "override_reason": override_reason,
        }

    # ── Private ────────────────────────────────────────────────────────────────

    def _emit_logged(
        self,
        correlation_id: str,
        input_str: str,
        command: str,
        rule_id: str,
        decision: str,
        override_reason: str,
    ):
        _logger.log_event(
            event_type     = "approval_logged",
            stage          = "approval_logged",
            correlation_id = correlation_id,
            input_str      = input_str,
            decision       = decision,
            reason         = override_reason,
            metadata       = {
                "actor_id":        self.operator_id,
                "command":         command,
                "rule_id":         rule_id,
                "override_reason": override_reason,
                "auto_deny":       self.auto_deny,
            },
        )
