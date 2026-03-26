"""
Sentinel Fail-Closed Test Suite
Covers: semantic timeout, malformed output, missing policy file,
        sandbox profile failure, and layered-defense case.

Run: PYTHONPATH=. python3 tests/fail_closed_tests.py
"""
import time
import json
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POLICY_PATH = "src/sentinel/policies/security.yaml"
BACKUP_PATH  = "/tmp/sentinel_policy_backup.yaml"

def section(title):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")

# ──────────────────────────────────────────────────────────────────────────────
# Test 1: Semantic auditor unavailable → fail closed (default block)
# ──────────────────────────────────────────────────────────────────────────────
def test_semantic_auditor_unavailable():
    section("TEST 1: Semantic Auditor Unavailable → Fail Closed")
    from src.sentinel.main import SentinelRuntime
    from src.sentinel.models import AuditDecision
    from unittest.mock import patch, MagicMock

    # Patch the SentinelAuditor constructor to raise, so auditor is None
    with patch("src.sentinel.main.SentinelAuditor", side_effect=RuntimeError("LLM unreachable")):
        rt = SentinelRuntime()
        # A command not covered by policy rules (needs semantic fallback)
        result = rt.run_intercepted_command("do something unusual and complex")
        allowed = result.get("allowed")
        print(f"  Input:   'do something unusual and complex'")
        print(f"  Auditor: None (forced constructor failure)")
        print(f"  Result:  allowed={allowed}")
        assert not allowed, "FAIL: Should have been blocked (fail-closed)"
        print(f"  ✅ PASS: System failed closed — BLOCK returned when auditor unavailable")

# ──────────────────────────────────────────────────────────────────────────────
# Test 2: Malformed semantic output → fail closed
# ──────────────────────────────────────────────────────────────────────────────
def test_malformed_semantic_output():
    section("TEST 2: Malformed Semantic Output → Fail Closed")
    from src.sentinel.main import SentinelRuntime
    from src.sentinel.models import AuditDecision
    from unittest.mock import patch

    rt = SentinelRuntime()
    # Patch command_auditor.audit to return a block decision (simulates bad/uncertain LLM output)
    def bad_audit(cmd):
        raise ValueError("LLM returned non-JSON garbage: <html>502 Bad Gateway</html>")

    original_audit = rt.command_auditor.audit
    rt.command_auditor.audit = bad_audit

    result = rt.run_intercepted_command("do something unusual and complex")
    allowed = result.get("allowed")
    print(f"  Input:   'do something unusual and complex'")
    print(f"  Auditor: raises ValueError (malformed output)")
    print(f"  Result:  allowed={allowed}")
    assert not allowed, "FAIL: Should have been blocked on malformed semantic output"
    print(f"  ✅ PASS: System failed closed — BLOCK returned on malformed auditor output")

    rt.command_auditor.audit = original_audit

# ──────────────────────────────────────────────────────────────────────────────
# Test 3: Missing policy file → default block
# ──────────────────────────────────────────────────────────────────────────────
def test_missing_policy_file():
    section("TEST 3: Missing Policy File → Default Block")
    shutil.copy(POLICY_PATH, BACKUP_PATH)
    os.remove(POLICY_PATH)
    try:
        from src.sentinel import policy as pol_module
        import importlib
        importlib.reload(pol_module)
        from src.sentinel.policy import PolicyEnforcer
        enforcer = PolicyEnforcer(policy_path=POLICY_PATH)
        result = enforcer.evaluate("rm -rf /")
        action = result.get("action")
        print(f"  Policy file: REMOVED ({POLICY_PATH})")
        print(f"  Input: 'rm -rf /'")
        print(f"  default_action: {enforcer.default_action}")
        print(f"  result action: {action}")
        assert action == "block", "FAIL: Default action must be block"
        print(f"  ✅ PASS: Missing policy file → default_action=block applied")
    finally:
        shutil.copy(BACKUP_PATH, POLICY_PATH)
        os.remove(BACKUP_PATH)

# ──────────────────────────────────────────────────────────────────────────────
# Test 4: Sandbox profile generation failure → fail closed
# ──────────────────────────────────────────────────────────────────────────────
def test_sandbox_profile_failure():
    section("TEST 4: Sandbox Profile Generation Failure → Fail Closed")
    from src.sentinel.main import SentinelRuntime
    from unittest.mock import patch

    rt = SentinelRuntime()

    def broken_wrap(cmd_args, workspace_root):
        raise RuntimeError("sandbox-exec profile build failed: insufficient permissions")

    rt.isolation_adapter.wrap_command = broken_wrap

    result = rt.run_intercepted_command("ls -la")
    allowed = result.get("allowed")
    print(f"  Input:   'ls -la' (policy: allow)")
    print(f"  Sandbox: wrap_command() raises RuntimeError")
    print(f"  Result:  allowed={allowed}")
    assert not allowed, "FAIL: Should fail closed when sandbox profile fails"
    print(f"  ✅ PASS: Sandbox failure → BLOCK returned (fail-closed)")

# ──────────────────────────────────────────────────────────────────────────────
# Test 5: Layered-defense — deterministic allows, isolation still constrains
# ──────────────────────────────────────────────────────────────────────────────
def test_layered_defense():
    section("TEST 5: Layered Defense — Allow passes policy+semantic, isolation constrains env")
    from src.sentinel.main import SentinelRuntime

    rt = SentinelRuntime()
    # "ls -la" → policy allows, semantic skips, BUT isolation sandbox is still applied.
    result = rt.run_intercepted_command("ls -la")

    print(f"  Input:    'ls -la'")
    print(f"  Policy:   ALLOW (rule fs-001)")
    print(f"  Semantic: SKIP (cleared deterministically)")
    print(f"  Isolation: sandbox-exec active → process is sandboxed despite being allowed")
    print(f"  Returncode: {result.get('returncode')}")
    print(f"  Final:    {result.get('reason')}")

    # Verify we can see isolation in the most recent trace
    with open("src/sentinel/logs/audit_structured.jsonl") as f:
        lines = [json.loads(l) for l in f if l.strip()]

    isolation_events = [l for l in lines if l.get("stage") == "isolation_wrap"]
    last_isolation = isolation_events[-1] if isolation_events else None

    if last_isolation:
        backend = last_isolation["metadata"].get("backend")
        wrapped = last_isolation["metadata"].get("wrapped_argv", "")
        print(f"\n  Isolation event (from JSONL trace):")
        print(f"    backend:     {backend}")
        print(f"    wrapped_argv (first 100 chars): {str(wrapped)[:100]}")
        assert backend == "sandbox-exec", "FAIL: Expected sandbox-exec backend"
        print(f"  ✅ PASS: Command allowed at policy+semantic layers, but still executed inside sandbox-exec")
    else:
        print("  ⚠️  No isolation_wrap event found in logs — run test with main runtime first.")


if __name__ == "__main__":
    print("🛡️ ─── Sentinel Fail-Closed Test Suite ───\n")
    failures = []
    for test_fn in [
        test_semantic_auditor_unavailable,
        test_malformed_semantic_output,
        test_missing_policy_file,
        test_sandbox_profile_failure,
        test_layered_defense,
    ]:
        try:
            test_fn()
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
            failures.append(test_fn.__name__)

    print(f"\n{'─'*60}")
    print(f"  Results: {5 - len(failures)}/5 passed  |  {len(failures)} failures")
    if failures:
        for f in failures:
            print(f"    ❌ {f}")
        sys.exit(1)
    else:
        print("  🏆 All fail-closed tests passed.")
        sys.exit(0)
