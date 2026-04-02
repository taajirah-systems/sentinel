import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from src.ledger.ledger import read_wallets, write_wallets, ACCOUNTING_LOG, INTEGRITY_LOG
from src.ledger.holds import HoldManager
from src.governance.db import SentinelDB
from src.ledger.validation import validate_hierarchy_link
from src.ledger.ledger_service import get_available_jul, allocate_child_credit, spend_service_credit

def setup_test_env():
    """Clear logs for a clean forensic run."""
    # Ensure ledger directory exists
    Path("ledger").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    if os.path.exists(ACCOUNTING_LOG):
        open(ACCOUNTING_LOG, "w").close()
    if os.path.exists(INTEGRITY_LOG):
        open(INTEGRITY_LOG, "w").close()
    
    # Initialize baseline wallets
    wallets = {
        "org_hq": {"wallet_id": "org_hq", "wallet_type": "org", "balance_jul": 1000.0, "held_jul": 0.0},
        "proj_alpha": {"wallet_id": "proj_alpha", "wallet_type": "project", "parent_wallet_id": "org_hq", "balance_jul": 0.0, "held_jul": 0.0},
        "agent_007": {"wallet_id": "agent_007", "wallet_type": "agent", "parent_wallet_id": "proj_alpha", "balance_jul": 0.0, "held_jul": 0.0}
    }
    write_wallets(wallets)
    print("✅ Test Environment Initialized.")

def test_layered_cap_enforcement():
    print("\n[PROOF] Testing Layered Cap Enforcement...")
    
    # 1. Org -> Project (Valid)
    res = allocate_child_credit("org_hq", "proj_alpha", 500.0, "funding_p1", "Project Alpha Budget")
    assert res is not None
    
    # 2. Project -> Agent (Valid)
    res = allocate_child_credit("proj_alpha", "agent_007", 100.0, "funding_a1", "Agent 007 Budget")
    assert res is not None
    
    wallets = read_wallets()
    assert wallets["org_hq"]["balance_jul"] == 500.0
    assert wallets["proj_alpha"]["balance_jul"] == 400.0
    assert wallets["agent_007"]["balance_jul"] == 100.0
    
    # 3. Exceed Parent Cap (Invalid)
    # Proj Alpha only has 400 left. Attempt to give 500 to Agent.
    res = allocate_child_credit("proj_alpha", "agent_007", 500.0, "overrun_p1", "Invalid Overrun")
    assert res is None
    
    # Check Integrity Log for HIERARCHY_ALLOC_SHORTFALL
    caught_violation = False
    if os.path.exists(INTEGRITY_LOG):
        with open(INTEGRITY_LOG, "r") as f:
            for line in f:
                if "HIERARCHY_ALLOC_SHORTFALL" in line:
                    caught_violation = True
                    break
    assert caught_violation, "Expected HIERARCHY_ALLOC_SHORTFALL in integrity log."
    print("✅ Layered Cap Enforcement (Org/Project/Agent) Verified.")

def test_shortfall_fail_closed():
    print("\n[PROOF] Testing Shortfall Fail-Closed Logic...")
    hm = HoldManager()
    
    # 1. Create Hold (10 JUL)
    hold_id = hm.create_hold(
        "agent_007", 10.0, "req_s1", "Shortfall Test", 
        project_id="proj_alpha", org_id="org_hq"
    )
    
    # agent_007 has 100 balance. 10 is held. Available = 90.
    # 2. Settle with massive shortfall (Actual 110 JUL, Estimated 10 JUL, Shortfall 100 JUL)
    # Available (90) < Shortfall (100) -> FAIL CLOSED
    success = hm.settle_hold(
        hold_id, "agent_007", actual_amount_jul=110.0, estimated_amount_jul=10.0,
        description="Massive Overspend Attempt", correlation_id="id_s1"
    )
    assert success is False
    
    # 3. Verify budget_shortfall event in authoritative ledger
    caught_shortfall = False
    with open(ACCOUNTING_LOG, "r") as f:
        for line in f:
            if "budget_shortfall" in line:
                caught_shortfall = True
                break
    assert caught_shortfall, "Expected budget_shortfall in accounting ledger."
    
    # 4. Settle with acceptable shortfall (Actual 20 JUL, Estimated 10 JUL, Shortfall 10 JUL)
    # Available (90) > Shortfall (10) -> SUCCESS
    # Note: Need new hold because first failed
    hold_id_2 = hm.create_hold("agent_007", 10.0, "req_s2", "Valid Shortfall Test", project_id="p1", org_id="o1")
    success = hm.settle_hold(
        hold_id_2, "agent_007", actual_amount_jul=20.0, estimated_amount_jul=10.0,
        description="Acceptable Variance", correlation_id="id_s2"
    )
    assert success is True
    
    wallets = read_wallets()
    # 100 initial - 20 actual = 80
    assert wallets["agent_007"]["balance_jul"] == 80.0
    print("✅ Shortfall Fail-Closed and Variance Absorption Verified.")

def test_strict_state_machine():
    print("\n[PROOF] Testing Strict State Machine Transitions...")
    hm = HoldManager()
    hold_id = hm.create_hold("agent_007", 5.0, "req_t1", "State Transition Proof", project_id="p1", org_id="o1")
    
    # 1. Active -> Settled (Valid)
    res = hm.settle_hold(hold_id, "agent_007", 5.0, 5.0, "Valid Settle", "id_t1")
    assert res is True
    
    # 2. Settled -> Released (Invalid)
    success = hm.release_hold(hold_id, "agent_007", 5.0, "Attempt to double-release", "id_t2")
    assert success is False
    
    # Check Integrity Log for INVALID_STATE_TRANSITION
    caught_violation = False
    with open(INTEGRITY_LOG, "r") as f:
        for line in f:
            if "INVALID_STATE_TRANSITION" in line:
                caught_violation = True
                break
    assert caught_violation, "Expected INVALID_STATE_TRANSITION in integrity log."
    print("✅ Strict State Machine Transitions Verified.")

def generate_evidence_pack():
    print("\n[SYSTEM] Generating Technical Evidence Pack...")
    from src.governance.db import SentinelDB
    db = SentinelDB()
    hm = HoldManager()
    
    # 1. Active Hold Row
    hold_id = hm.create_hold("agent_007", 1.0, "req_ev1", "Evidence Pack Creation", project_id="proj_alpha", org_id="org_hq")
    hold = db.get_hold(hold_id)
    with open("evidence_hold_active.json", "w") as f:
        json.dump(hold, f, indent=2)
    
    # 2. History Row (Settled)
    hm.settle_hold(hold_id, "agent_007", 0.8, 1.0, "Evidence Settlement", "id_ev1")
    history = db.get_hold(hold_id)
    with open("evidence_hold_history.json", "w") as f:
        json.dump(history, f, indent=2)
        
    print("✅ Evidence Pack Generated.")

if __name__ == "__main__":
    setup_test_env()
    try:
        test_layered_cap_enforcement()
        test_shortfall_fail_closed()
        test_strict_state_machine()
        generate_evidence_pack()
        print("\n[SUMMARY] All high-integrity proofs PASSED.")
    except Exception as e:
        print(f"\n❌ Proof Failure: {e}")
        import traceback
        traceback.print_exc()
