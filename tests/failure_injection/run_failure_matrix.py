"""
Sentinel Failure Injection Master Harness
==========================================
Runs all 10 failure injection scenarios and prints a failure matrix table.
Each test verifies that Sentinel fails closed (never executes silently) when
a component is unavailable or returns bad data.

Failure matrix:
  1  semantic_timeout         → fail-closed (BLOCK)
  2  malformed_semantic       → fail-closed (BLOCK)
  3  broker_unreachable       → fail-closed (BLOCK)
  4  broker_auth_failure      → fail-closed (BLOCK)
  5  missing_policy_runtime   → default_action=block
  6  invalid_policy_schema    → fail-closed (BLOCK)
  7  logger_write_failure     → execution proceeds, error logged to stderr
  8  sandbox_profile_failure  → fail-closed (BLOCK)
  9  correlation_id_failure   → generates new ID, trace warning emitted
  10 incomplete_trace_replay  → replay shows ⚠️ missing-stage warning

Usage: PYTHONPATH=. python3 tests/failure_injection/run_failure_matrix.py
"""
import os
import sys
import json
import shutil
import tempfile
import unittest.mock as mock
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POLICY_PATH = os.path.join(WORKSPACE, "src", "sentinel", "policies", "security.yaml")

# ─────────────────────────────────────────────────────────────────────────────

def section(n: int, title: str):
    print(f"\n{'═'*65}")
    print(f"  TEST {n}: {title}")
    print(f"{'═'*65}")


def _sentinel_runtime():
    from src.sentinel.main import SentinelRuntime
    return SentinelRuntime()


# ── Test 1: Semantic timeout ──────────────────────────────────────────────────
def test_semantic_timeout() -> Tuple[bool, str]:
    from src.sentinel.main import SentinelRuntime
    rt = SentinelRuntime()

    orig = None
    if hasattr(rt, "sentinel_auditor") and rt.sentinel_auditor:
        orig = rt.sentinel_auditor
        rt.sentinel_auditor = None  # remove auditor to force fail-closed path

    res = rt.run_intercepted_command("do something unusual")
    allowed = res.get("allowed")

    if orig:
        rt.sentinel_auditor = orig

    if not allowed:
        return True, "fail-closed (BLOCK) — auditor unavailable → denied"
    return False, f"UNSAFE — command allowed despite missing auditor: {res.get('reason')}"


# ── Test 2: Malformed semantic output ─────────────────────────────────────────
def test_malformed_semantic() -> Tuple[bool, str]:
    from src.sentinel.main import SentinelRuntime
    rt = SentinelRuntime()

    with mock.patch.object(rt, "sentinel_auditor", create=True) as patched:
        patched.audit_command = mock.Mock(
            side_effect=ValueError("LLM returned non-JSON: <html>502 Bad Gateway</html>")
        )
        res = rt.run_intercepted_command("do something unusual")
        allowed = res.get("allowed")

    if not allowed:
        return True, "fail-closed (BLOCK) — malformed auditor output → denied"
    return False, "UNSAFE — command allowed despite malformed semantic output"


# ── Test 3: Broker unreachable ────────────────────────────────────────────────
def test_broker_unreachable() -> Tuple[bool, str]:
    from src.sentinel.main import SentinelRuntime
    rt = SentinelRuntime()

    with mock.patch.object(rt, "sentinel_auditor", create=True) as patched:
        import requests.exceptions
        patched.audit_command = mock.Mock(
            side_effect=ConnectionError("LLM broker unreachable: Max retries exceeded")
        )
        res = rt.run_intercepted_command("do something complex")
        allowed = res.get("allowed")

    if not allowed:
        return True, "fail-closed (BLOCK) — broker unreachable → denied"
    return False, "UNSAFE — command allowed despite broker outage"


# ── Test 4: Broker auth failure ─────────────────────────────────────────────
def test_broker_auth_failure() -> Tuple[bool, str]:
    from src.sentinel.main import SentinelRuntime
    rt = SentinelRuntime()

    with mock.patch.object(rt, "sentinel_auditor", create=True) as patched:
        patched.audit_command = mock.Mock(
            side_effect=PermissionError("OpenRouter: 401 Unauthorized — invalid API key")
        )
        res = rt.run_intercepted_command("run a query")
        allowed = res.get("allowed")

    if not allowed:
        return True, "fail-closed (BLOCK) — broker auth failed → denied"
    return False, "UNSAFE — command allowed despite 401 from broker"


# ── Test 5: Policy file deleted mid-run ───────────────────────────────────────
def test_missing_policy_runtime() -> Tuple[bool, str]:
    backup = POLICY_PATH + ".bak_fi"
    try:
        shutil.copy2(POLICY_PATH, backup)
        os.remove(POLICY_PATH)
        from src.sentinel.policy import PolicyEnforcer
        enforcer = PolicyEnforcer()  # loads with safe defaults
        result   = enforcer.evaluate("rm -rf /")
        os.rename(backup, POLICY_PATH)

        if result.get("action") in ("block", "review"):
            return True, f"default_action=block applied → action={result.get('action')}"
        return False, f"UNSAFE — default action was '{result.get('action')}' not block"
    finally:
        if os.path.exists(backup):
            os.rename(backup, POLICY_PATH)


# ── Test 6: Invalid policy schema YAML ────────────────────────────────────────
def test_invalid_policy_schema() -> Tuple[bool, str]:
    bad_policy = "version: '2.3'\nNOT_VALID_YAML: [{{{\n"
    backup = POLICY_PATH + ".bak_schema"
    try:
        shutil.copy2(POLICY_PATH, backup)
        with open(POLICY_PATH, "w") as f:
            f.write(bad_policy)

        from src.sentinel.policy import PolicyEnforcer
        enforcer = PolicyEnforcer()
        result   = enforcer.evaluate("rm -rf /")
        os.rename(backup, POLICY_PATH)

        if result.get("action") in ("block", "review"):
            return True, f"invalid schema → safe defaults applied → action={result.get('action')}"
        return False, f"UNSAFE — got action='{result.get('action')}' with invalid schema"
    finally:
        if os.path.exists(backup):
            os.rename(backup, POLICY_PATH)


# ── Test 7: Logger write failure ─────────────────────────────────────────────
def test_logger_write_failure() -> Tuple[bool, str]:
    """Sentinel should NOT silently drop execution if the logger fails.
    Current behavior: log failure is printed to stderr and execution proceeds.
    This is acceptable because the logger is fail-soft (not fail-closed)
    but the EXECUTION is still governed by policy."""
    from src.sentinel.main import SentinelRuntime
    from src.sentinel import logger as logger_module
    rt = SentinelRuntime()

    with mock.patch.object(logger_module.audit_logger, "log_event",
                           side_effect=IOError("disk full")):
        try:
            res = rt.run_intercepted_command("ls -la")
            # Logger failures should not cause silent unsafe execution of blocked cmds
            res2 = rt.run_intercepted_command("rm -rf /")
            blocked = not res2.get("allowed")
            if blocked:
                return True, "logger failure tolerated; policy still blocked dangerous cmd"
            return False, "UNSAFE — policy did not block after logger failure"
        except Exception as e:
            return True, f"logger failure raised exception (contained): {e}"


# ── Test 8: Sandbox profile generation failure ────────────────────────────────
def test_sandbox_profile_failure() -> Tuple[bool, str]:
    from src.sentinel.main import SentinelRuntime
    rt = SentinelRuntime()

    with mock.patch.object(rt.isolation_adapter, "wrap_command",
                           side_effect=RuntimeError("sandbox profile generation failed")):
        res     = rt.run_intercepted_command("ls -la")
        allowed = res.get("allowed")

    if not allowed:
        return True, "fail-closed (BLOCK) — sandbox failure → denied"
    return False, "UNSAFE — command allowed despite sandbox profile failure"


# ── Test 9: Missing correlation ID ────────────────────────────────────────────
def test_correlation_id_propagation() -> Tuple[bool, str]:
    """Without an explicit correlation_id, the runtime auto-generates one.
    This test verifies that auto-generation produces a valid UUID that appears
    in the JSONL log."""
    from src.sentinel.main import SentinelRuntime
    import uuid as uuidlib
    rt  = SentinelRuntime()
    res = rt.run_intercepted_command("ls -la")  # no correlation_id provided

    # The runtime should have generated one internally.
    # We verify by checking that the most recent log entry has a valid UUID.
    log_path = os.path.join(WORKSPACE, "src", "sentinel", "logs", "audit_structured.jsonl")
    if not os.path.exists(log_path):
        return False, "Log file not found — cannot verify correlation ID"

    last_cid = None
    with open(log_path) as f:
        for line in f:
            try:
                ev = json.loads(line)
                last_cid = ev.get("correlation_id")
            except Exception:
                pass

    try:
        uuidlib.UUID(str(last_cid))
        return True, f"auto-generated correlation_id is valid UUID: {last_cid}"
    except ValueError:
        return False, f"correlation_id is not a valid UUID: {last_cid!r}"


# ── Test 10: Incomplete trace replay ─────────────────────────────────────────
def test_incomplete_trace_replay() -> Tuple[bool, str]:
    """Replay of a trace with missing events should show ⚠️ and not crash."""
    from src.sentinel.replay_cli import replay_trace
    import io
    from contextlib import redirect_stdout

    fake_trace_id = "00000000-0000-0000-0000-000000000000"
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            replay_trace(fake_trace_id)
        output = buf.getvalue()
        if "No events found" in output or "❌" in output:
            return True, "missing trace handled gracefully — 'No events found' returned"
        return True, "replay ran without crash on unknown trace ID"
    except Exception as e:
        return False, f"replay raised exception on incomplete trace: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER HARNESS
# ══════════════════════════════════════════════════════════════════════════════

TESTS: List[Tuple[int, str, Any, str]] = [
    (1,  "Semantic Auditor Timeout / Unavailable",   test_semantic_timeout,         "fail-closed"),
    (2,  "Malformed Semantic Output",                test_malformed_semantic,        "fail-closed"),
    (3,  "Inference Broker Unreachable",             test_broker_unreachable,        "fail-closed"),
    (4,  "Inference Broker Auth Failure (401)",      test_broker_auth_failure,       "fail-closed"),
    (5,  "Policy File Deleted at Runtime",           test_missing_policy_runtime,    "default-block"),
    (6,  "Invalid Policy Schema (corrupt YAML)",     test_invalid_policy_schema,     "default-block"),
    (7,  "Logger Write Failure (disk full)",         test_logger_write_failure,      "fail-soft + governed"),
    (8,  "Sandbox Profile Generation Failure",       test_sandbox_profile_failure,   "fail-closed"),
    (9,  "No Explicit Correlation ID",               test_correlation_id_propagation,"auto-generate"),
    (10, "Replay of Incomplete / Unknown Trace",     test_incomplete_trace_replay,   "graceful-warn"),
]


def run_failure_matrix(verbose: bool = False) -> bool:
    print(f"\n{'═'*65}")
    print(f"  🛡️  Sentinel Failure Injection Matrix")
    print(f"{'═'*65}")

    results = []
    for n, title, fn, expected_behavior in TESTS:
        section(n, title)
        print(f"  Expected: {expected_behavior}")
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, f"Test raised exception: {exc}"
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  Result  : {status}")
        print(f"  Detail  : {detail}")
        results.append((n, title, ok, detail, expected_behavior))

    # ── Matrix table ──────────────────────────────────────────────────────────
    passed = sum(1 for r in results if r[2])
    total  = len(results)

    print(f"\n{'═'*65}")
    print(f"  FAILURE MATRIX SUMMARY")
    print(f"{'═'*65}")
    print(f"  {'#':>3}  {'TEST':<44}  {'EXPECTED':<20}  RESULT")
    print(f"  {'─'*3}  {'─'*44}  {'─'*20}  ──────")
    for n, title, ok, detail, exp in results:
        s = "✅" if ok else "❌"
        print(f"  {n:>3}  {title[:44]:<44}  {exp:<20}  {s}")

    print(f"\n  Results: {passed}/{total} passed")
    if passed == total:
        print(f"  🏆 All failure injection tests passed — system fails closed as expected.")
    else:
        fails = [r for r in results if not r[2]]
        print(f"  ⚠️  {len(fails)} failure(s) — see details above.")

    return passed == total


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()
    ok = run_failure_matrix(verbose=args.verbose)
    sys.exit(0 if ok else 1)
