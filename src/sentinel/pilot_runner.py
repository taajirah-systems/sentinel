import os
import uuid
import time
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

from src.ledger.holds import HoldManager
from src.governance.approvals import ApprovalManager
from src.ledger.ledger import read_wallets

class PilotRunner:
    """
    Orchestrates the isolated Sentinel Pilot v1.
    Truth Layers: Ledger, Holds DB, Reconciled Cache.
    """
    def __init__(self, pilot_dir: str = "/Users/taajirah_systems/sentinel/pilot_v1"):
        self.pilot_dir = Path(pilot_dir)
        self.evidence_dir = self.pilot_dir / "evidence"
        self.hm = HoldManager()
        self.am = ApprovalManager()
        
        self.wallet_tree = {
            "org": "org_pilot",
            "project": "proj_pilot",
            "agent": "agent_coder"
        }
        
        # Scenario Definitions
        self.scenarios = [
            {"id": "T1", "name": "Normal Flow", "est": 50.0, "actual": 48.5, "risk": 3},
            {"id": "T2", "name": "Gated Flow", "est": 150.0, "actual": 142.0, "risk": 8},
            {"id": "T3a", "name": "Shortfall -> Release", "est": 30.0, "actual": 400.0, "risk": 4, "override": "release"},
            {"id": "T3b", "name": "Shortfall -> Fund", "est": 30.0, "actual": 400.0, "risk": 4, "override": "fund_and_settle"}
        ]

    def snapshot(self, label: str):
        """Captures raw state of all truth layers."""
        snap_dir = self.evidence_dir / label
        snap_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Ledger Layer
        ledger_src = Path(os.getenv("SENTINEL_LEDGER_DIR", "/Users/taajirah_systems/sentinel/ledger"))
        for log in ["accounting.jsonl", "governance.jsonl", "integrity_events.jsonl"]:
            if (ledger_src / log).exists():
                shutil.copy(ledger_src / log, snap_dir / log)
        
        # 2. Cache Layer
        if (ledger_src / "wallets.json").exists():
            shutil.copy(ledger_src / "wallets.json", snap_dir / "wallets.json")
            
        # 3. Database Layer
        db_src = Path(os.getenv("SENTINEL_DB_PATH", "data/sentinel.db"))
        if db_src.exists():
            shutil.copy(db_src, snap_dir / "sentinel.db")
            
        print(f"[AUDIT] Snapshot '{label}' captured.")

    def run_scenarios(self):
        print(f"--- PILOT START: {datetime.now(timezone.utc).isoformat()} ---")
        self.snapshot("00_baseline")

        for s in self.scenarios:
            print(f"\n[SCENARIO] {s['id']}: {s['name']}")
            
            hold_id = None
            req_id = None

            # 1. GATED FLOW (T2)
            if s['risk'] > 7:
                print(f"[PILOT] Requesting gated approval for {s['id']}...")
                req_id = self.am.create_request(
                    command=f"exec {s['id']}",
                    rule_name="RiskGate",
                    reason=f"Risk {s['risk']} > 7",
                    wallet_id=self.wallet_tree["agent"],
                    agent_id="agent_coder",
                    project_id=self.wallet_tree["project"],
                    org_id=self.wallet_tree["org"],
                    estimated_cost_jul=s['est'],
                    risk_score=s['risk']
                )
                if not req_id:
                    print(f"❌ [PILOT] Approval Request Failed for {s['id']}.")
                    continue
                
                # Fetch the hold_id created by AM
                req = self.am.get_request(req_id)
                hold_id = req.hold_id
                
                self.snapshot(f"{s['id']}_01_hold")
                self.snapshot(f"{s['id']}_02_pending")
                
                print(f"[PILOT] Resolving request {req_id}...")
                self.am.resolve_request(req_id, "approved", "admin_01", "Pilot Auto-Approve")
                self.snapshot(f"{s['id']}_03_approved")

            # 2. NORMAL FLOW (T1, T3a, T3b)
            else:
                hold_id = self.hm.create_hold(
                    wallet_id=self.wallet_tree["agent"],
                    amount_jul=s['est'],
                    correlation_id=s['id'],
                    description=f"Pilot {s['id']}",
                    project_id=self.wallet_tree["project"],
                    org_id=self.wallet_tree["org"]
                )
                self.snapshot(f"{s['id']}_01_hold")

            if not hold_id:
                print(f"❌ [PILOT] Hold Creation Failed for {s['id']}.")
                continue

            # 3. SETTLE
            success = self.hm.settle_hold(
                hold_id=hold_id,
                wallet_id=self.wallet_tree["agent"],
                actual_amount_jul=s['actual'],
                estimated_amount_jul=s['est'],
                description=f"Settle {s['id']}",
                correlation_id=s['id']
            )
            
            # 4. OVERRIDE (T3a / T3b)
            if not success:
                hold_record = self.hm.db.get_hold(hold_id)
                if hold_record["status"] == "failed_shortfall":
                    self.snapshot(f"{s['id']}_04_clamped")
                    print(f"[PILOT] Overriding clamped hold {hold_id} via '{s['override']}'...")
                    self.hm.resolve_clamped_hold(
                        hold_id=hold_id,
                        wallet_id=self.wallet_tree["agent"],
                        resolution_mode=s['override'],
                        audit_reason="Pilot Oversight Override",
                        operator_id="admin_01"
                    )
                    self.snapshot(f"{s['id']}_05_overridden")
            else:
                self.snapshot(f"{s['id']}_04_settled")

        print(f"\n--- PILOT COMPLETE: {datetime.now(timezone.utc).isoformat()} ---")

if __name__ == "__main__":
    runner = PilotRunner()
    runner.run_scenarios()
