"""
Sentinel Structured Audit Logger
Produces per-stage append-only JSONL events that can be replayed by trace ID.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ── Canonical version fields ─────────────────────────────────────────────────
SENTINEL_VERSION = "0.1.0"   # product / binary version (semver)
POLICY_VERSION   = "2.4"     # policy document version (increments with rule changes)
SCHEMA_VERSION   = "3.1"     # JSONL schema version (increments with field additions)

# ── Stage constants ───────────────────────────────────────────────────────────
STAGE_INTAKE          = "intake"
STAGE_NORMALIZE       = "normalization"
STAGE_REDACT          = "redaction"
STAGE_POLICY_EVAL     = "policy_evaluation"
STAGE_SEMANTIC_AUDIT  = "semantic_audit"
STAGE_ISOLATION_WRAP  = "isolation_wrap"
STAGE_EXEC_RESULT     = "execution_result"
STAGE_FINAL_DECISION  = "final_decision"
STAGE_RUNTIME_DENIAL  = "runtime_denial"   # sandbox rejected at execution time


class AuditLogger:
    """
    Append-only, per-stage structured JSONL logger for Sentinel audit events.

    Each log line carries three separate version fields:
      sentinel_version – binary / product version
      policy_version   – policy rule set version
      schema_version   – JSONL schema version

    Multiple events share a correlation_id so the full trace can be reconstructed.
    """

    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_event(
        self,
        event_type: str,
        input_str: str,
        correlation_id: Optional[str] = None,
        normalized_input: Optional[str] = None,
        decision: Optional[str] = None,
        reason: Optional[str] = None,
        agent_id: str = "default-agent",
        metadata: Optional[Dict[str, Any]] = None,
        stage: Optional[str] = None,
    ) -> str:
        """Emit one JSONL audit event. Returns the correlation_id used."""
        cid = correlation_id or str(uuid.uuid4())
        event: Dict[str, Any] = {
            # ── identity & versioning (three separate fields) ─────────────────
            "schema_version":   SCHEMA_VERSION,
            "sentinel_version": SENTINEL_VERSION,
            "policy_version":   POLICY_VERSION,
            # ── trace ─────────────────────────────────────────────────────────
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "correlation_id":   cid,
            "stage":            stage or event_type,
            "event_type":       event_type,
            # ── subject ───────────────────────────────────────────────────────
            "agent_id":         agent_id,
            "input":            input_str,
            "normalized_input": normalized_input,
            # ── outcome ───────────────────────────────────────────────────────
            "decision":         decision,
            "reason":           reason,
            "metadata":         metadata or {},
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event) + "\n")
        return cid


# ── Default instance ─────────────────────────────────────────────────────────
_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_LOG_PATH = os.path.join(_THIS_DIR, "logs", "audit_structured.jsonl")
_log_path    = os.getenv("SENTINEL_AUDIT_LOG_PATH", _DEFAULT_LOG_PATH)
audit_logger = AuditLogger(_log_path)
