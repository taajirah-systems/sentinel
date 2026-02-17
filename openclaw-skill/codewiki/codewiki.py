#!/usr/bin/env python3
"""
Code Wiki Skill for OpenClaw
Allows agents to ingest and query architecture documentation.
"""
import sys
import json
import time
from typing import Any, Dict

def ingest(url: str) -> Dict[str, Any]:
    """
    Simulates ingesting a documentation page.
    """
    print(f"DEBUG: Ingesting from {url}...")
    # Simulate network latency
    time.sleep(0.5)
    
    return {
        "status": "success",
        "url": url,
        "summary": f"Documentation from {url} has been indexed.",
        "topics": ["Architecture", "API", "Security"],
        "diagrams": [f"{url}/diagram1.png"]
    }

def query(url: str, question: str) -> Dict[str, Any]:
    """
    Simulates querying the documentation.
    """
    print(f"DEBUG: Querying {url} with question: '{question}'")
    time.sleep(0.5)
    
    return {
        "status": "success",
        "question": question,
        "answer": f"This is a simulated answer for '{question}' based on the docs at {url}. The architecture follows standard Sentinel patterns.",
        "confidence": 0.95
    }

def handle(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenClaw entry point.
    """
    # Determine which tool was called based on params or implicit context if available
    # OpenClaw might pass the tool name in params? Or we infer from keys.
    
    # In skill.yaml, we map DIFFERENT tools to this SAME handler.
    # Usually OpenClaw calls the handler associated with the tool name.
    # But here the handler is the file. 
    # Let's assume params might contain 'url' and optionally 'question'.
    
    url = params.get("url")
    if not url:
        return {"error": "Missing 'url' parameter"}
        
    question = params.get("question")
    
    if question:
        return query(url, question)
    else:
        return ingest(url)

if __name__ == "__main__":
    # CLI Mode for manual testing or subprocess execution
    import argparse
    
    parser = argparse.ArgumentParser(description="Code Wiki Skill")
    parser.add_argument("action", choices=["ingest", "query"], help="Action to perform")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--question", help="Question for query action")
    
    args = parser.parse_args()
    
    if args.action == "ingest":
        print(json.dumps(ingest(args.url), indent=2))
    elif args.action == "query":
        if not args.question:
            print("Error: --question is required for query action")
            sys.exit(1)
        print(json.dumps(query(args.url, args.question), indent=2))
