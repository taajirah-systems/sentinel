from sentinel.command_auditor import CommandAuditor
from sentinel.models import AuditDecision
from sentinel.sentinel_auditor import SentinelAuditor

__all__ = ["AuditDecision", "CommandAuditor", "SentinelAuditor", "SentinelRuntime"]


def __getattr__(name: str):
    if name == "SentinelRuntime":
        from sentinel_main import SentinelRuntime

        return SentinelRuntime
    raise AttributeError(f"module 'sentinel' has no attribute {name!r}")
