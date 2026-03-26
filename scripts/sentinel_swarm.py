#!/usr/bin/env python3
import subprocess
import json
import sys

def run_agent(agent_id, message):
    print(f"--- Calling {agent_id.capitalize()} ---")
    cmd = [
        "openclaw", "agent",
        "--agent", agent_id,
        "--message", message,
        "--json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"error": "Failed to parse agent output", "raw": result.stdout}

def main():
    if len(sys.argv) < 2:
        print("Usage: ./sentinel_swarm.py <complex_task>")
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    
    print(f"🚀 Initializing Sentinel Swarm for task: {task}\n")

    # Phase 1: Research
    research_query = f"Research the context and requirements for: {task}"
    research_results = run_agent("researcher", research_query)
    
    # Phase 2: Architect Plan
    architect_query = f"Based on this research, create a plan for: {task}. Research: {json.dumps(research_results)}"
    plan = run_agent("architect", architect_query)
    
    # Phase 3: Execute
    executor_query = f"Execute the following plan: {json.dumps(plan)}"
    execution_results = run_agent("executor", executor_query)
    
    # Phase 4: Audit
    audit_query = f"Audit the following execution results for safety and correctness: {json.dumps(execution_results)}"
    audit_report = run_agent("auditor", audit_query)
    
    print("\n--- Final Swarm Report ---")
    print(json.dumps(audit_report, indent=2))

if __name__ == "__main__":
    main()
