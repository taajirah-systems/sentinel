#!/usr/bin/env python3
"""
Sentinel Admin Tools for OpenClaw
Allows the agent to interact with the Sentinel Server for HITL approvals.
"""
import sys
import os
import json
import urllib.request
import urllib.error

# Config
SENTINEL_HOST = os.getenv("SENTINEL_HOST", "127.0.0.1")
SENTINEL_PORT = os.getenv("SENTINEL_PORT", "8765")
BASE_URL = f"http://{SENTINEL_HOST}:{SENTINEL_PORT}"
TOKEN = os.getenv("SENTINEL_AUTH_TOKEN", "")

HEADERS = {
    "X-Sentinel-Token": TOKEN,
    "Content-Type": "application/json"
}

def list_pending() -> dict:
    try:
        req = urllib.request.Request(f"{BASE_URL}/pending", headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        return {"error": f"Failed to connect to Sentinel: {e}"}
    except Exception as e:
        return {"error": str(e)}

def approve_request(request_id: str) -> dict:
    try:
        url = f"{BASE_URL}/approve/{request_id}"
        req = urllib.request.Request(url, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
            return {"error": err_body.get("detail", str(e))}
        except:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # OpenClaw tool interface
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command provided"}))
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "list_pending":
        print(json.dumps(list_pending()))
    elif cmd == "approve":
        if len(sys.argv) < 3:
             print(json.dumps({"error": "Missing request_id"}))
        else:
             print(json.dumps(approve_request(sys.argv[2])))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
