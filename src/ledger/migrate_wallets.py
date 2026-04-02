import json
from pathlib import Path
import sys

# Compute the path to the ledger directory relative to this script
LEDGER_DIR = Path(__file__).resolve().parents[2] / "ledger"
WALLETS_FILE = LEDGER_DIR / "wallets.json"

def migrate_wallets():
    if not WALLETS_FILE.exists():
        print(f"No wallets file found at {WALLETS_FILE}. Migration skipped.")
        return

    # Create a backup
    backup_file = WALLETS_FILE.with_suffix(".json.bak")
    with open(WALLETS_FILE, "r", encoding="utf-8") as f:
        wallets = json.load(f)
        
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(wallets, f, indent=2)
    print(f"Backup created at {backup_file}")

    migrated_count = 0
    for recipient, wallet in wallets.items():
        # Add new default schema keys if missing
        if "kyc_verified" not in wallet:
            wallet["kyc_verified"] = False
            migrated_count += 1
        
        wallet.setdefault("contract_active", False)
        wallet.setdefault("reputation_score", 1.0)
        wallet.setdefault("monthly_settlement_limit_zar", 5000.0)
        wallet.setdefault("this_month_withdrawn_zar", 0.0)

    # Write migrated dict back
    with open(WALLETS_FILE, "w", encoding="utf-8") as f:
        json.dump(wallets, f, indent=2, ensure_ascii=False)
        
    print(f"Migration complete. Updated {migrated_count} wallets.")

if __name__ == "__main__":
    migrate_wallets()
