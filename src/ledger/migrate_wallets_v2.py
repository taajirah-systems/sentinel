import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from src.token.ledger import WALLETS_FILE

def migrate_to_v2():
    if not WALLETS_FILE.exists():
        print("No wallets.json found. Nothing to migrate.")
        return

    # Backup existing
    backup_path = WALLETS_FILE.with_suffix(".json.v1_backup")
    if not backup_path.exists():
        shutil.copy2(WALLETS_FILE, backup_path)
        print(f"Backed up {WALLETS_FILE.name} to {backup_path.name}")
    else:
        print(f"Backup already exists at {backup_path.name}, skipping backup creation.")

    # Load wallets
    with open(WALLETS_FILE, "r", encoding="utf-8") as f:
        wallets = json.load(f)

    migrated_count = 0
    skipped_count = 0
    review_count = 0

    now_iso = datetime.now(timezone.utc).isoformat()

    for wallet_id, data in wallets.items():
        # Check current schema
        if data.get("schema_version") == 2:
            skipped_count += 1
            continue

        migrated_count += 1
        data["schema_version"] = 2
        
        # Enforce wallet type
        if "wallet_type" not in data:
            if wallet_id.startswith("+27"):
                data["wallet_type"] = "contractor"
            else:
                data["wallet_type"] = "unknown"
                review_count += 1

        # Enforce KYC / Contract keys
        if "kyc_verified" not in data:
            data["kyc_verified"] = False
            data["kyc_verified_at"] = None
        else:
            if "kyc_verified_at" not in data and data["kyc_verified"]:
                data["kyc_verified_at"] = now_iso
                
        if "contract_active" not in data:
            data["contract_active"] = False
            data["contract_activated_at"] = None
        else:
            if "contract_activated_at" not in data and data["contract_active"]:
                data["contract_activated_at"] = now_iso

        if "reputation_score" not in data:
            data["reputation_score"] = 1.0
            data["reputation_last_updated_at"] = now_iso
            data["reputation_last_updated_by"] = "system_migration"

        # Explicit compliance default for contractors
        if data["wallet_type"] == "contractor":
            if "monthly_settlement_limit_zar" not in data:
                data["monthly_settlement_limit_zar"] = 5000.0
            if "compliance_last_updated_at" not in data:
                data["compliance_last_updated_at"] = now_iso
            if "compliance_last_updated_by" not in data:
                data["compliance_last_updated_by"] = "system_migration"

    # Write back
    tmp = WALLETS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(wallets, f, indent=2, ensure_ascii=False)
    tmp.replace(WALLETS_FILE)

    print("\n--- Migration Summary ---")
    print(f"Total Wallets Parsed: {len(wallets)}")
    print(f"Migrated to v2: {migrated_count}")
    print(f"Skipped (already v2): {skipped_count}")
    
    if review_count > 0:
        print(f"⚠️ WARNING: {review_count} wallets flagged as 'unknown' type requiring manual review.")
        print("Please check wallets.json and manually verify internal/client vs contractor roles.")
    else:
        print("✅ No manual reviews required. All types mapped safely.")

if __name__ == "__main__":
    migrate_to_v2()
