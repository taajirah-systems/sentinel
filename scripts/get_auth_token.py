#!/usr/bin/env python3
import requests
import json
import sys

def get_token(agent_id, secret):
    """
    Fetches a Firebase Auth Bearer token from the local Federation Auth Gateway.
    
    Args:
        agent_id (str): The ID of the requesting agent (e.g., 'executor', 'researcher')
        secret (str): The pre-shared gateway secret
    """
    url = "http://127.0.0.1:18889/token"
    payload = {"agent_id": agent_id, "secret": secret}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        print(token_data.get("token"))
        return token_data.get("token")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching token: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 get_auth_token.py <agent_id> <secret>")
        sys.exit(1)

    agent_id = sys.argv[1]
    secret = sys.argv[2]
    get_token(agent_id, secret)
