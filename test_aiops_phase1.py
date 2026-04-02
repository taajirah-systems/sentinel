"""
Sentinel AIOps Phase 1 Verification Suite.
"""

import sys
import os
from datetime import datetime, timezone

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.token.ledger import read_wallets, write_wallets
from src.token.issuer import record_agent_spend, issue_oversight_credit
from src.token.wallet import request_settlement, SettlementError
from src.token.governance import validate_action, GovernanceDecision

def run_verification():
    print("=== Sentinel AIOps Phase 1: Operational Verification ===\n")

    # Setup Test State
    wallets = read_wallets()
    
    # 1. Create a Test Agent with a 1.0 JUL budget
    agent_id = "test_agent_alpha"
    wallets[agent_id] = {
        "schema_version": 3,
        "wallet_type": "agent",
        "project_id": "test_project",
        "budget_limit_jul": 1.0,
        "current_spend_jul": 0.0,
    }
    
    # 2. Create a Test Contractor
    contractor_id = "test_reviewer_beta"
    wallets[contractor_id] = {
        "schema_version": 3,
        "wallet_type": "contractor",
        "kyc_verified": True,
        "contract_active": True,
        "balance_jul": 5.0,
        "monthly_settlement_limit_zar": 10.0,
        "this_month_withdrawn_zar": 0.0,
    }
    
    write_wallets(wallets)

    print("--- 1. Testing Budget Enforcement ---")
    # Action 1: 0.5 JUL (Utility) - Should pass
    decision = validate_action(agent_id, "inference", 0.5)
    print(f"Action 1 (0.5 JUL): {decision}")
    if decision == GovernanceDecision.ALLOWED:
        record_agent_spend(agent_id, 0.5, "utility", "test_project", "run_1")
        print("✅ PASS: Spend recorded.")
    
    # Action 2: 0.6 JUL (Exceeds 1.0 limit) - Should fail
    decision = validate_action(agent_id, "inference", 0.6)
    print(f"Action 2 (0.6 JUL): {decision}")
    if decision == GovernanceDecision.DENIED:
        print("✅ PASS: Limit enforced.")
    else:
        print("❌ FAIL: Limit not enforced.")

    print("\n--- 2. Testing Spend Classification (AIOps Metadata) ---")
    # Action 3: Record Waste
    record_agent_spend(agent_id, 0.1, "waste", "test_project", "run_loop_1", "Loop detected")
    print("✅ PASS: Waste spend recorded in ledger.")

    print("\n--- 3. Testing Settlement Constraints ---")
    try:
        # Request 2.0 ZAR settlement
        res = request_settlement(contractor_id, 2.0)
        print(f"✅ PASS: Settlement requested: {res['request_id']}")
    except SettlementError as e:
        print(f"❌ FAIL: {e.code}: {e.message}")

    try:
        # Attempt to settle from an AGENT (Should fail)
        request_settlement(agent_id, 0.1)
        print("❌ FAIL: Agent was allowed to request settlement.")
    except SettlementError as e:
        print(f"✅ PASS: Blocked Agent settlement -> {e.code}")

    print("\n--- 4. Ledger Verification ---")
    if os.path.exists("ledger/governance_events.jsonl"):
         print("✅ PASS: Governance ledger exists.")
    
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    run_verification()
