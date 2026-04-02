import os
import json
import time
from src.ledger.holds import HoldManager
from src.ledger.ledger import read_wallets, write_wallets, iter_accounting_events

def test_manual_override_modes():
    print("[TEST] Initializing Manual Override Modes Verification...")
    hm = HoldManager()
    
    # 1. Setup
    wallets = read_wallets()
    w_id = "test_cleanup_wallet"
    wallets[w_id] = {
        "id": w_id,
        "name": "Cleanup Test Wallet",
        "balance_jul": 200.0,
        "held_jul": 0.0,
        "hard_limit_jul": 2000.0,
        "parent_wallet_id": "test_org"
    }
    write_wallets(wallets)
    
    # 2. Test MODE: release
    print("[TEST] Verifying 'release' mode...")
    h1 = hm.create_hold(w_id, 50.0, "c1", "Hold 1", "p1", "o1")
    hm.db.update_hold_status(h1, "failed_shortfall") # Force clamp for test
    
    res = hm.resolve_clamped_hold(h1, w_id, "release", "Manual cleanup", "admin_01")
    assert res is True
    assert hm.db.get_hold(h1)["status"] == "released"
    assert read_wallets()[w_id]["held_jul"] == 0.0
    print("✅ 'release' mode verified.")

    # 3. Test MODE: fund_and_settle (Shortfall Absorption)
    print("[TEST] Verifying 'fund_and_settle' mode...")
    h2 = hm.create_hold(w_id, 100.0, "c2", "Hold 2", "p1", "o1")
    hm.db.update_hold_status(h2, "failed_shortfall") # Force clamp for test
    
    res = hm.resolve_clamped_hold(h2, w_id, "fund_and_settle", "Bypass for short", "admin_02")
    assert res is True
    assert hm.db.get_hold(h2)["status"] == "settled"
    # Final check on audit fields in ledger
    found_audit = False
    for event in iter_accounting_events():
        if event["event_type"] == "hold_manually_settled_with_funding" and event["metadata"].get("hold_id") == h2:
            meta = event["metadata"]
            # Verify 7 mandatory fields (some are implicit in metadata or parent event)
            assert meta["actor_id"] == "admin_02"
            assert meta["reason"] == "Bypass for short"
            assert meta["previous_state"] == "failed_shortfall"
            assert meta["new_state"] == "settled"
            assert meta.get("hold_id") == h2
            assert "correlation_id" in meta
            assert "timestamp" in meta
            found_audit = True
            break
    assert found_audit is True
    print("✅ 'fund_and_settle' mode + 7 audit fields verified.")

    # 4. Test MODE: force_settle
    print("[TEST] Verifying 'force_settle' mode...")
    h3 = hm.create_hold(w_id, 30.0, "c3", "Hold 3", "p1", "o1")
    hm.db.update_hold_status(h3, "failed_shortfall") # Force clamp
    res = hm.resolve_clamped_hold(h3, w_id, "force_settle", "Operational force", "admin_03")
    assert res is True
    assert hm.db.get_hold(h3)["status"] == "settled"
    print("✅ 'force_settle' mode verified.")

if __name__ == "__main__":
    try:
        test_manual_override_modes()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
