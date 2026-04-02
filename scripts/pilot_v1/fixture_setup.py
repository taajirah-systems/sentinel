import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# 1. PATH CONFIGURATION
BASE_DIR = Path("/Users/taajirah_systems/sentinel/pilot_v1")
LEDGER_DIR = BASE_DIR / "ledger"
DB_PATH = BASE_DIR / "sentinel.db"
WALLETS_PATH = LEDGER_DIR / "wallets.json"

def setup_fixture():
    print(f"--- INITIALIZING PILOT FIXTURE: {BASE_DIR} ---")
    
    # 2. CLEANUP
    if BASE_DIR.exists():
        import shutil
        shutil.rmtree(BASE_DIR)
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "evidence").mkdir(parents=True, exist_ok=True)

    # 3. BASELINE WALLETS
    now = datetime.now(timezone.utc).isoformat()
    wallets = {
        "org_pilot": {
            "wallet_id": "org_pilot",
            "wallet_type": "org",
            "balance_jul": 5000.0,
            "held_jul": 0.0,
            "created_at": now,
            "last_reconciled_at": now
        },
        "proj_pilot": {
            "wallet_id": "proj_pilot",
            "parent_wallet_id": "org_pilot",
            "wallet_type": "project",
            "balance_jul": 1000.0,
            "held_jul": 0.0,
            "created_at": now,
            "last_reconciled_at": now
        },
        "agent_coder": {
            "wallet_id": "agent_coder",
            "parent_wallet_id": "proj_pilot",
            "wallet_type": "agent",
            "balance_jul": 300.0,
            "held_jul": 0.0,
            "created_at": now,
            "last_reconciled_at": now
        }
    }

    with open(WALLETS_PATH, "w") as f:
        json.dump(wallets, f, indent=2)
    print(f"✅ Baseline wallets initialized: {WALLETS_PATH}")

    # 4. INITIALIZE DB
    from src.governance.db import SentinelDB
    db = SentinelDB(str(DB_PATH))
    print(f"✅ Fresh Sentinel DB initialized: {DB_PATH}")

    # 5. INITIALIZE EMPTY LOGS
    for log in ["accounting.jsonl", "governance.jsonl", "integrity_events.jsonl"]:
        (LEDGER_DIR / log).touch()
    print("✅ Empty audit logs initialized.")

if __name__ == "__main__":
    setup_fixture()
