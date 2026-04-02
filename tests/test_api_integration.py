import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add sentinel to pythonpath
sentinel_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(sentinel_dir))

from src.api.server import app
from src.token.wallet import get_balance

def test_chat_proxy():
    print("\n--- 🛡️ Testing Sentinel API Proxy (Epic 1 & 3) 🛡️ ---")
    
    # Fake payload with leaking IP and API key
    payload = {
        "model": "google/gemini-pro",
        "messages": [
            {
                "role": "system",
                "content": "You are a NemoClaw agent."
            },
            {
                "role": "user",
                "content": "Please analyze this database: mysql://root:AIzaFakeKey123@192.168.1.104/db. Also # this is a comment\n    \n    "
            }
        ],
        "temperature": 0.5
    }
    
    # We expect a 500 error because we don't have a real API key configured in the env,
    # OR we expect it to hit the openrouter/google proxy and fail.
    # What we REALLY care about is that the SCRUB pipeline ran and didn't crash before that.
    
    print("\n1. Sending request to /v1/chat/completions...")
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload)
        print(f"Status: {response.status_code} (Expected 500 if NO API KEY, or 200 if valid)")
        print(f"Detail: {response.text}")
        print("\nIf you look at the console logs above, you should see '🛡️ [SCRUB] Saved ...' indicating the intercept worked.")

def test_hitl_approval():
    print("\n2. Testing HITL Approval JOULE reward...")
    # Get current balance
    initial_balance = get_balance("+27658623499")
    print(f"Initial Admin Balance: {initial_balance} JOULE")
    
    # To approve, we need a pending request ID.
    # We will just simulate a failed audit to generate one.
    with TestClient(app) as client:
        audit_resp = client.post("/audit", json={"command": "rm -rf /"})
        print(f"Audit Status: {audit_resp.status_code}")
        data = audit_resp.json()
        
        # Extract the Request ID
        req_id = None
        reason = data.get("reason", "")
        if "Request ID:" in reason:
            import re
            match = re.search(r"\[Request ID:\s*([\w-]+)\]", reason)
            if match:
                req_id = match.group(1)
                
        if req_id:
            print(f"Got Pending Request ID: {req_id}")
            app_resp = client.post(f"/approve/{req_id}")
            print(f"Approve Status: {app_resp.status_code}")
            
            final_balance = get_balance("+27658623499")
            print(f"Final Admin Balance: {final_balance} JOULE")
            print(f"Balance Delta: {final_balance['balance_jul'] - initial_balance['balance_jul']} JOULE (Should be +50 for verification)")
        else:
            print(f"Reason: {reason}")
            print("Could not extract Request ID (Make sure 'rm -rf /' was blocked by policy and generated a review request)")

if __name__ == "__main__":
    test_chat_proxy()
    test_hitl_approval()
