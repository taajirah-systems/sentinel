import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sentinel.main import SentinelRuntime

def run_demo():
    """
    Runtime Containment Demo
    ========================
    Proves that OS-enforced sandboxing blocks access to sensitive files
    even if the Sentinel policy layer is completely bypassed (HITL override).
    
    Target: cat /private/etc/passwd
    Expected: Policy allows (via bypass), but macOS Seatbelt Sandbox denies (exit != 0).
    """
    print("🛡️  Sentinel Runtime Containment Demo")
    print("   Attempting to read /private/etc/passwd with explicit HITL bypass = True.")
    
    runtime = SentinelRuntime()
    result = runtime.run_intercepted_command(
        cmd_string="cat /private/etc/passwd",
        bypass_policy=True  # Simulates operator explicitly allowing this via HITL
    )

    print("\n" + "="*60)
    print("  FINAL DECISION")
    print("  Verdict   :", result.get("decision", "unknown").upper())
    print("  Reason    :", result.get("reason", "unknown"))
    
    if result.get("sandbox_denial"):
        print("  ✅ SUCCESS: OS-level sandbox explicitly denied the operation at runtime.")
        print(f"     Target match  : /private/etc/passwd")
        print(f"     Stderr snippet: {result.get('stderr', '').strip()[:50]}...")
    else:
        print("  ❌ FAILURE: Sandbox did not fire or command succeeded.")
    print("="*60)
    
    print(f"\nReplay trace ID: {result.get('correlation_id')}")
    print(f"Run: python3 src/sentinel/replay_cli.py {result.get('correlation_id')}")

if __name__ == "__main__":
    run_demo()
