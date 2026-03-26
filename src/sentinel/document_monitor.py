import time
import os
from pathlib import Path
from src.sentinel.agents.document_auditor import DocumentAuditor
from src.sentinel.db import SentinelDB

WATCH_DIR = Path("data/logistics")
CHECK_INTERVAL = 5  # seconds

def monitor_logistics():
    db = SentinelDB()
    auditor = DocumentAuditor()
    
    # Ensure watch directory exists
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Monitoring {WATCH_DIR.absolute()} for new documents...")
    
    processed_files = set()
    
    # Pre-populate already existing files to avoid re-auditing everything on start
    for f in WATCH_DIR.iterdir():
        if f.is_file():
            processed_files.add(f.name)

    try:
        while True:
            for f in WATCH_DIR.iterdir():
                if f.is_file() and f.name not in processed_files:
                    print(f"📄 New document detected: {f.name}")
                    result = auditor.audit_document(f)
                    
                    # Log to DB (using the audit_logs table for now, or we could add a new one)
                    # We'll adapt log_audit to handle document details
                    db.log_audit(f"DOC_AUDIT: {f.name}", result)
                    
                    print(f"✅ Audit complete for {f.name}. Allowed: {result.get('allowed')}")
                    processed_files.add(f.name)
            
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped.")

if __name__ == "__main__":
    monitor_logistics()
