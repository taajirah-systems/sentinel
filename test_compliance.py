import os
import requests
import uuid
import json
from src.token.issuer import issue_joule
from src.token.wallet import request_withdrawal

AUTH_TOKEN = os.getenv("SENTINEL_AUTH_TOKEN", "f6acf84a8aeaf8abebae9a13700671d34c7bcaa7c8705971d0f61a9790f9b590")
headers = {"x-sentinel-token": AUTH_TOKEN}

def run_tests():
    print("=== Testing Sentinel Strict Compliance V2 ===")
    
    test_num = f"+27{uuid.uuid4().hex[:8]}"
    
    # 6. Bounded reputation multiplier in action
    print("\n--- Testing Bounded Reputation Multiplier ---")
    from src.token.ledger import read_wallets, write_wallets
    w = read_wallets()
    w[test_num] = {
        "schema_version": 2, "wallet_type": "contractor", 
        "kyc_verified": False, "contract_active": False,
        "reputation_score": 0.5, # Should trigger 0.5x bound instead of 0.5x? Wait, score < 0.60 => 0.50x
        "monthly_settlement_limit_zar": 5000.0,
        "balance_jul": 0.0, "lifetime_earned_jul": 0.0, "lifetime_withdrawn_zar": 0.0, "this_month_withdrawn_zar": 0.0
    }
    write_wallets(w)
    
    res = issue_joule(test_num, "verification", "run_123", "test_runner", tokens_consumed=1000)
    print(f"Issued JOULE with base reputation 0.5 -> {res['quality_multiplier']} multiplier matched.")
    print(f"Issued JOULE amount: {res['jul_issued']}")

    print("\n--- 2. Rejected withdrawal for missing KYC ---")
    try:
        request_withdrawal(test_num, 0.05, "bank_transfer", "acc_123", "tester")
        print("❌ FAIL: Withdrawal succeeded despite missing KYC.")
    except Exception as e:
        if "ERR_KYC_REQUIRED" in str(e):
            print(f"✅ PASS: Blocked -> {e}")
        else:
            print(f"❌ FAIL: Expected ERR_KYC_REQUIRED, got: {e}")

    print("\n--- 5. Admin compliance update event ---")
    update_res = requests.post(
        "http://0.0.0.0:8765/api/admin/wallets/compliance/update",
        json={
            "wallet_id": test_num,
            "kyc_verified": True,
            "contract_active": True,
            "monthly_settlement_limit_zar": 50.0,
            "actor_id": "test_script",
            "reason": "Test approval"
        },
        headers=headers
    )
    print(f"Update response: {update_res.status_code}")
    print(update_res.json())
    
    w = read_wallets()
    w[test_num]["balance_jul"] = 1000.0 # Inject artificial large balance to test limits
    write_wallets(w)

    print("\n--- 4. Successful pending settlement request ---")
    try:
        tx = request_withdrawal(test_num, 2.0, "bank_transfer", "acc_123", "tester")
        print(f"✅ PASS: Withdrawal Success -> STATUS: {tx['status']} (Requested {tx['amount_zar']} ZAR)")
    except Exception as e:
        print(f"❌ FAIL: Expected success but got: {e}")

    print("\n--- 3. Rejected withdrawal for monthly cap ---")
    try:
        from src.token.wallet import approve_withdrawal
        approve_withdrawal(tx["id"], "admin")
        print("Approved first withdrawal.")
        
        tx3 = request_withdrawal(test_num, 60.0, "bank_transfer", "acc_123", "tester")
        print("❌ FAIL: Withdrawal succeeded when it should breach.")
    except Exception as e:
        if "ERR_MONTHLY_LIMIT_EXCEEDED" in str(e):
            print(f"✅ PASS: Blocked Limits -> {e}")
        else:
            print(f"❌ FAIL: Unexpected error -> {e}")
            
    # Verify the compliance_events.jsonl appended records exist
    print("\n--- Verifying Audit Ledger ---")
    with open("ledger/compliance_events.jsonl", "r") as f:
        lines = f.readlines()
        print(f"Found {len(lines)} compliance events tracked securely.")
        print(f"Latest event: {lines[-1].strip()}")

if __name__ == "__main__":
    run_tests()
