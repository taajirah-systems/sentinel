import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sentinel.main import SentinelRuntime

def run_demo():
    """
    Benign Execution Demo
    =====================
    Demonstrates a safe command that passes the Sentinel v2.4 policy
    and executes successfully in the local environment.
    
    Target: python3 --version
    Expected: Policy allows, command succeeds.
    """
    print("🛡️  Sentinel Benign Execution Demo")
    print("   Command: python3 --version")
    
    runtime = SentinelRuntime()
    result = runtime.run_intercepted_command(
        cmd_string="python3 --version"
    )

    print("\n" + "="*60)
    print("  FINAL DECISION")
    print("  Verdict   :", result.get("decision", "unknown").upper())
    print("  Reason    :", result.get("reason", "unknown"))
    print("  Stdout    :", result.get("stdout", "").strip())
    
    if result.get("decision") == "allow":
        print("  ✅ SUCCESS: Benign command cleared and executed.")
    else:
        print("  ❌ FAILURE: Command blocked.")
    print("="*60)
    
    print(f"\nReplay trace ID: {result.get('correlation_id')}")

if __name__ == "__main__":
    run_demo()
