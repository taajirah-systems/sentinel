import os
import sys
import unittest.mock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sentinel.main import SentinelRuntime

def run_demo():
    """
    Operator Approval Flow Demo
    ===========================
    Demonstrates a successful human-in-the-loop approval for a review-gated command.
    
    Target: python3 -c "print('hello')"
    Expected: Policy prompts for review; operator approves; execution succeeds.
    """
    print("🛡️  Sentinel Operator Approval Flow Demo")
    print("   Target: python3 -c \"print('hello')\"")
    
    # Identify the approving operator
    os.environ["SENTINEL_OPERATOR_ID"] = "analyst-01"
    
    runtime = SentinelRuntime()
    
    # Simulation: Operator provides reason and approval
    with unittest.mock.patch('builtins.input', side_effect=["Security inspection for demo", "approve"]):
        result = runtime.run_intercepted_command(
            cmd_string="python3 -c \"print('hello')\""
        )

    print("\n" + "="*60)
    print("  FINAL DECISION")
    print("  Verdict   :", result.get("decision", "unknown").upper())
    print("  Reason    :", result.get("reason", "unknown"))
    print("  Stdout    :", result.get("stdout", "").strip())
    print("  Actor     : analyst-01")
    
    if result.get("decision") == "allow":
        print("  ✅ SUCCESS: Interactive approval flow captured in trace.")
    else:
        print("  ❌ FAILURE: Approval denied or execution failed.")
    print("="*60)
    
    print(f"\nReplay trace ID: {result.get('correlation_id')}")
    print(f"Run: python3 src/sentinel/replay_cli.py {result.get('correlation_id')}")

if __name__ == "__main__":
    run_demo()
