import json
from pathlib import Path
import sys

# Add src to path
sys.path.append(".")

from src.ledger.ledger import INTEGRITY_LOG, iter_accounting_events

events = []
# 1. Integrity Violations
if INTEGRITY_LOG.exists():
    with open(INTEGRITY_LOG, "r") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
                
# 2. Authoritative Budget Shortfalls
for event in iter_accounting_events():
    if event.get("event_type") == "budget_shortfall":
        events.append(event)
        
# Sort by timestamp desc
events.sort(key=lambda x: x.get("timestamp", x.get("_written_at", "")), reverse=True)

print(json.dumps(events[:5], indent=2))
