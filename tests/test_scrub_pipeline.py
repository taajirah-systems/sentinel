import sys
from pathlib import Path
import json

# Setup imports
sentinel_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(sentinel_dir))

from src.scrub.pipeline import scrub_payload

# Fake "leaked" document payload
RAW_PROMPT = """
You are acting as the Sentinel OpenClaw Trading Agent.

Please analyze the following trading strategy for the Dirty Sandbox in the NemoClaw infrastructure.
If the error rate exceeds 5%, ping the systems team at admin@anti-gravity.co.za or call +27725834268.

The database connection string is:
mysql://root:AIzaSyB-fake-gemini-key-1234567890abcdefg@192.168.1.104/trades

Also, user profile data to consider:
Name: John Doe
ID: 8504235012081

# Code block to review:
def execute_trade(token_pair):
    
    
    # This is a critical proprietary trading algorithm component
    # Do not leak this!
    
    print(f"Executing trade on {token_pair}")
    
    
    return True
"""

if __name__ == "__main__":
    print("--- 🛡️ Sovereign Scrub Pipeline Test 🛡️ ---\n")
    print("[RAW INPUT]")
    print(RAW_PROMPT)
    print("------------------------------------------\n")
    
    clean_text, metrics = scrub_payload(RAW_PROMPT)
    
    print("[CLEAN OUTPUT]")
    print(clean_text)
    print("\n------------------------------------------")
    print("[METRICS]")
    print(json.dumps(metrics, indent=2))
