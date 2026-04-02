import os
import json
import time
from src.ledger.ledger import read_wallets, write_wallets, ACCOUNTING_LOG, INTEGRITY_LOG
from src.ledger.holds import HoldManager
from src.governance.db import SentinelDB

def test_state_repair():
    print("Testing Governance State Repair...")
    hm = HoldManager()
    db = SentinelDB()
    
    # 1. Setup clean baseline
    wallets = {
        "repair_agent": {"wallet_id": "repair_agent", "wallet_type": "agent", "balance_jul": 100.0, "held_jul": 0.0}
    }
    write_wallets(wallets)
    
    # 2. Create authoritative holds in DB
    hm.create_hold("repair_agent", 10.0, "req_r1", "Repair Test 1", project_id="p1", org_id="o1")
    hm.create_hold("repair_agent", 20.0, "req_r2", "Repair Test 2", project_id="p1", org_id="o1")
    
    # 3. Verify initial state
    wallets = read_wallets()
    assert wallets["repair_agent"]["held_jul"] == 30.0
    print("✅ Authoritative holds created (30 JUL held).")
    
    # 4. SIMULATE CORRUPTION: Mangle the wallet cache
    wallets["repair_agent"]["held_jul"] = 999.0
    write_wallets(wallets)
    print("⚠️ Wallet cache mangled (999 JUL held).")
    
    # 5. EXECUTE REPAIR
    hm.repair_held_jul_cache()
    
    # 6. VERIFY REPAIR
    wallets = read_wallets()
    print(f"Repaired held_jul: {wallets['repair_agent']['held_jul']}")
    assert wallets["repair_agent"]["held_jul"] == 30.0
    print("✅ Authoritative repair successful (Cache restored from DB).")

if __name__ == "__main__":
    print("Running State Stability Verification...")
    test_state_repair()
    print("\n✅ Stability Suite PASSED.")
