from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditDecision:
    allowed: bool
    risk_score: int
    reason: str
    insight: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_score": int(max(0, min(10, self.risk_score))),
            "reason": self.reason,
            "insight": self.insight
        }

    @classmethod
    def reject(cls, reason: str, risk_score: int = 10, insight: Optional[str] = None) -> "AuditDecision":
        return cls(allowed=False, risk_score=max(0, min(10, risk_score)), reason=reason, insight=insight)
