import os
import sys
from pathlib import Path
import time

# Add src to the path so we can import our modules
sentinel_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(sentinel_dir))

from src.token import oracle, issuer, wallet, ledger

def run_simulation():
    print("\n--- ⚡ JOULE Token System Simulation ⚡ ---")
    
    # 1. Start the Oracle
    print("\n[1] Starting the Valuation Oracle...")
    oracle.start_oracle()
    
    # Wait a moment for the cache to load/refresh
    time.sleep(1)
    
    rate = oracle.get_jul_to_zar()
    usd_rate = oracle.get_jul_to_usd()
    print(f"    Current Rate: 1 JOULE = R{rate:.2f} (≈ ${usd_rate:.4f})")
    
    # 2. Issue tokens for different contributions
    print("\n[2] Simulating Work & Issuing Tokens...")
    
    user_id = "+27658623499" # Your number
    
    # Scenario A: You provided some documents (data_upload)
    # The agent consumed 500,000 tokens on google-2 processing it.
    print("\n    -> Scenario A: Data Upload (500k tokens on google-2)")
    issuer.issue_joule(
        recipient=user_id,
        contribution_type="data_upload",
        agent_run_id="run_doc_index_001",
        approved_by="system",
        tokens_consumed=500000,
        provider="google-2"
    )
    
    # Scenario B: Human-in-the-loop (HITL) approval
    print("\n    -> Scenario B: HITL Verification")
    issuer.issue_joule(
        recipient=user_id,
        contribution_type="verification",
        agent_run_id="run_trade_exec_002",
        approved_by="system"
    )
    
    # 3. Check Wallet Balance
    print("\n[3] Checking Wallet Balance...")
    balance_info = wallet.get_balance(user_id)
    print(f"    User: {balance_info['recipient']}")
    print(f"    Balance: {balance_info['balance_jul']:.4f} JOULE")
    print(f"    Value: R{balance_info['balance_zar_equiv']:.2f}")
    
    # 4. Request a withdrawal
    print("\n[4] Requesting Withdrawal...")
    withdraw_amount = balance_info['balance_jul'] / 2 # Withdraw half
    
    tx = wallet.request_withdrawal(
        recipient=user_id,
        amount_jul=withdraw_amount,
        payout_method="fnb_account",
        payout_ref="62001122334",
        requested_by=user_id
    )
    
    print("\n    Current Wallet State after Request:")
    print(f"    {wallet.get_balance(user_id)}")
    
    # 5. Admin approves the withdrawal
    print("\n[5] Admin Approving Withdrawal (HITL)...")
    wallet.approve_withdrawal(tx_id=tx['id'], approved_by="admin_taajirah")
    
    print("\n    Final Wallet State:")
    print(f"    {wallet.get_balance(user_id)}")
    
    print("\n--- Simulation Complete ---")
    print("Check the generated JSONL files in the `/ledger` directory!")

if __name__ == "__main__":
    run_simulation()
