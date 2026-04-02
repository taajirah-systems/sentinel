import json
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timezone
from ..ledger.ledger import ACCOUNTING_LOG, iter_accounting_events, read_wallets

class AnalyticsAggregator:
    """
    Summarizes authoritative ledger events into governance and spend operations reports.
    """
    def __init__(self):
        self.log_path = ACCOUNTING_LOG

    def get_spend_operations_report(self, start_ts: float = 0.0, end_ts: float = float('inf')) -> Dict[str, Any]:
        """
        Calculates efficiency metrics: Value, Waste, Correction, and Blocked Ratios.
        """
        total_jul = 0.0
        success_jul = 0.0
        waste_jul = 0.0
        correction_jul = 0.0
        
        by_org = defaultdict(float)
        by_project = defaultdict(float)
        by_agent = defaultdict(float)
        by_outcome = defaultdict(int)
        
        # Load wallet index for org/project mapping
        wallets = read_wallets()
        
        task_count = 0
        success_count = 0
        
        if not self.log_path.exists():
            return self._empty_report()

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                event = json.loads(line)
                
                if event.get("event_type") != "spend":
                    continue
                
                # Timestamp filter (assuming Unix timestamp in metadata or record)
                # Fallback to _written_at if timestamp is missing
                raw_ts = event.get("timestamp") or event.get("_written_at")
                if isinstance(raw_ts, str):
                    try:
                        ts = datetime.fromisoformat(raw_ts).replace(tzinfo=timezone.utc).timestamp()
                    except ValueError:
                        continue
                else:
                    ts = raw_ts or 0.0

                if ts < start_ts or ts > end_ts:
                    continue
                
                amount = event.get("amount_jul") or 0.0
                total_jul += amount
                task_count += 1
                
                # Metadata extraction
                meta = event.get("metadata") or {}
                # Org/Project mapping from cache
                wallet = wallets.get(agent_id, {})
                org_id = event.get("org_id") or wallet.get("org_id") or "unknown"
                project_id = event.get("project_id") or wallet.get("project_id") or meta.get("project_id") or "default"
                
                by_org[org_id] += amount
                by_project[project_id] += amount
                by_agent[agent_id] += amount
                by_outcome[outcome] += 1
                
                if outcome == "completed":
                    success_count += 1
                    success_jul += amount
                
                if value_class == "waste":
                    waste_jul += amount
                elif value_class == "correction":
                    correction_jul += amount

        return {
            "summary": {
                "total_spend_jul": round(total_jul, 4),
                "success_jul": round(success_jul, 4),
                "waste_jul": round(waste_jul, 4),
                "correction_jul": round(correction_jul, 4),
                "waste_ratio": round(waste_jul / total_jul, 4) if total_jul > 0 else 0.0,
                "correction_ratio": round(correction_jul / total_jul, 4) if total_jul > 0 else 0.0,
                "cost_per_success_jul": round(success_jul / success_count, 4) if success_count > 0 else 0.0
            },
            "breakdown": {
                "by_org": dict(by_org),
                "by_project": dict(by_project),
                "by_agent": dict(by_agent),
                "by_outcome": dict(by_outcome)
            },
            "counts": {
                "total_tasks": task_count,
                "success_tasks": success_count
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "summary": {"total_spend_jul": 0, "waste_ratio": 0, "correction_ratio": 0},
            "breakdown": {"by_org": {}, "by_project": {}, "by_agent": {}, "by_outcome": {}},
            "counts": {"total_tasks": 0, "success_tasks": 0},
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def get_reconciliation_report(self) -> Dict[str, Any]:
        """
        Reports on hold estimation accuracy and budget shortfalls.
        """
        total_estimated = 0.0
        total_actual = 0.0
        total_surplus = 0.0
        total_shortfall = 0.0
        shortfall_count = 0
        
        for event in iter_accounting_events():
            e_type = event.get("event_type")
            if e_type == "hold_settled":
                meta = event.get("metadata") or {}
                total_estimated += meta.get("estimated_amount_jul", 0.0)
                total_actual += event.get("amount_jul", 0.0)
                total_surplus += meta.get("surplus_released_jul", 0.0)
                total_shortfall += meta.get("shortfall_drawn_jul", 0.0)
            elif e_type == "budget_shortfall":
                total_shortfall += event.get("amount_jul", 0.0)
                shortfall_count += 1
                
        return {
            "summary": {
                "total_estimated_jul": round(total_estimated, 4),
                "total_actual_jul": round(total_actual, 4),
                "total_surplus_jul": round(total_surplus, 4),
                "total_shortfall_jul": round(total_shortfall, 4),
                "estimation_accuracy_ratio": round(total_actual / total_estimated, 4) if total_estimated > 0 else 1.0,
                "shortfall_events": shortfall_count
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def get_governance_report(self) -> Dict[str, Any]:
        """
        Calculates governance efficiency: Human Save Rate and Override Frequency.
        """
        total_estimated_avoided = 0.0
        total_spend = 0.0
        override_count = 0
        approval_count = 0
        rejection_count = 0
        
        for event in iter_accounting_events():
            e_type = event.get("event_type")
            
            if e_type == "governance_resolved":
                meta = event.get("metadata") or {}
                status = meta.get("status")
                if status == "rejected":
                    rejection_count += 1
                    total_estimated_avoided += meta.get("estimated_cost_jul", 0.0)
                elif status == "approved":
                    approval_count += 1
            
            if e_type == "spend":
                total_spend += event.get("amount_jul", 0.0)
            
            if e_type and e_type.startswith("hold_manually_"):
                override_count += 1
                
        total_requests = approval_count + rejection_count
        
        return {
            "summary": {
                "human_save_rate": round(total_estimated_avoided / (total_spend + total_estimated_avoided), 4) if (total_spend + total_estimated_avoided) > 0 else 0.0,
                "operator_override_count": override_count,
                "approval_rate": round(approval_count / total_requests, 4) if total_requests > 0 else 1.0,
                "total_estimated_avoided_jul": round(total_estimated_avoided, 4)
            },
            "counts": {
                "approvals": approval_count,
                "rejections": rejection_count,
                "overrides": override_count
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
