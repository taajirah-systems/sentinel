import os
import time
import uuid
import json
from src.governance.approvals import ApprovalManager

def main():
    mgr = ApprovalManager()
    
    # 1. Creation: Expires in 2 seconds
    print("--- Creating Request (Expires in 2s) ---")
    req_id = mgr.create_request(
        command="rm -rf /",
        rule_name="Dangerous Command",
        reason="Triggered by heuristic",
        wallet_id="+27123456789",
        agent_id="test_exp_agent",
        ttl_seconds=2
    )
    
    req = mgr.get_request(req_id)
    print(f"Original Status: {req.status}")
    print(f"Expires At: {req.expires_at} (Current: {time.time()})")
    
    # 2. Wait for expiry
    print("\n--- Waiting for Expiry (3s) ---")
    time.sleep(3)
    
    # 3. Resolution Behavior (Attempting resolution post-expiry)
    print("\n--- Attempting Resolution post-expiry ---")
    # Note: The current resolve_request in approvals.py doesn't check expiry yet.
    # It just updates status. But we can trigger cleanup or check behavior.
    
    # Let's see if the DB layer has expiration enforcement.
    row_before = mgr.get_request(req_id)
    print(f"Status before purge: {row_before.status}")
    
    print("\n--- Triggering Cleanup of Expired Requests ---")
    mgr.cleanup_old_requests()
    
    # 4. Resulting Stored Status
    print("\n--- Final Status after Cleanup ---")
    row_after = mgr.get_request(req_id)
    if not row_after:
        print("Record purged successfully (Physical delete).")
    else:
        print(f"Record remains with status: {row_after.status}")

    # 5. Emitted Audit Record
    # (Checking the ledger for any record of this request/purge if implemented)

if __name__ == "__main__":
    main()
