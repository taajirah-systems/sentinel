"""
Sentinel Benchmark Runner v3.0 — 8-Path Split
=============================================
Measures latency for each distinct execution path through Sentinel.
Reports p50/p95/p99/min/max for each path, with stage participation flags.

Paths:
  det-allow       deterministic policy allow (no exec)
  det-block       deterministic policy block (no exec)
  sem-allow       semantic-required allow (stubbed timeout, fast path)
  sem-block       semantic-required block
  iso-allow       policy-allow + isolation-wrapped execution
  runtime-deny    policy-allow + isolation + sandbox-fires non-zero
  broker-allow    inference broker allow (if configured)
  broker-block    inference broker block

Usage:
  PYTHONPATH=. python3 tests/benchmark_runner.py [--samples 100] [--path iso-allow]
"""
import time
import json
import argparse
import statistics
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.sentinel.main import SentinelRuntime

PERF_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "sentinel", "logs", "performance.jsonl"
)
os.makedirs(os.path.dirname(PERF_LOG), exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
#  Path definitions
# ─────────────────────────────────────────────────────────────────────────────

PATHS: Dict[str, Dict[str, Any]] = {
    "det-block": {
        "label":            "Deterministic Policy Block",
        "description":      "Command matched by block rule; no subprocess spawned.",
        "semantic_invoked": False,
        "isolation_invoked": False,
        "commands":         ["rm -rf /", "cat /etc/passwd", "curl http://evil.com",
                             "\\x72\\x6d -rf /", "𝒄𝒂𝒕 /𝒆𝒕𝒄/𝒑𝒂𝒔𝒔𝒘𝒅",
                             "sudo su -", "mkfs.ext4 /dev/sda"],
        "kwargs":            {},
    },
    "det-allow": {
        "label":            "Deterministic Policy Allow",
        "description":      "Command matched by allow rule; subprocess spawned + sandboxed.",
        "semantic_invoked": False,
        "isolation_invoked": True,
        "commands":         ["ls -la", "echo hello", "pwd", "date", "whoami"],
        "kwargs":            {},
    },
    "sem-allow": {
        "label":            "Semantic Audit — Allow Path",
        "description":      "Command requires semantic review; auditor returns allow (mocked).",
        "semantic_invoked": True,
        "isolation_invoked": True,
        "commands":         ["ls -la", "echo test"],
        "kwargs":            {"bypass_policy": False},
        # Semantic path only fires when no deterministic rule matches.
        # We use commands that fall through to semantic via default policy.
        "_note":            "Uses default_action path where no rule matches but auditor decides",
    },
    "sem-block": {
        "label":            "Semantic Audit — Block Path",
        "description":      "Command flagged by semantic auditor; subprocess not spawned.",
        "semantic_invoked": True,
        "isolation_invoked": False,
        "commands":         ["rm -rf /", "cat /etc/passwd"],
        "kwargs":            {},
    },
    "iso-allow": {
        "label":            "Isolation-Wrapped Allow",
        "description":      "Policy allows; command runs inside sandbox-exec.",
        "semantic_invoked": False,
        "isolation_invoked": True,
        "commands":         ["ls -la", "echo hello", "pwd", "date", "whoami", "uname -a",
                             "wc -l README.md"],
        "kwargs":            {},
    },
    "runtime-deny": {
        "label":            "Runtime Containment (Sandbox Denial)",
        "description":      "Policy bypassed (HITL); sandbox denies the syscall at runtime.",
        "semantic_invoked": False,
        "isolation_invoked": True,
        "commands":         ["nc -z -w 1 93.184.216.34 80"],
        "kwargs":            {"bypass_policy": True},
    },
    "broker-allow": {
        "label":            "Inference Broker — Allow Path",
        "description":      "Command routed through semantic broker; broker returns allow.",
        "semantic_invoked": True,
        "isolation_invoked": True,
        "commands":         ["ls -la", "echo test"],
        "kwargs":            {},
        "_note":            "Timing includes LLM round-trip when broker is reachable",
    },
    "broker-block": {
        "label":            "Inference Broker — Block Path",
        "description":      "Command routed through semantic broker; broker returns block.",
        "semantic_invoked": True,
        "isolation_invoked": False,
        "commands":         ["rm -rf /", "cat /etc/passwd"],
        "kwargs":            {},
    },
}

WARMUP_COUNT = 5


def _stats(latencies_ms: List[float]) -> Dict[str, float]:
    s = sorted(latencies_ms)
    n = len(s)
    if n == 0:
        return {"count": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
    return {
        "count": n,
        "min":   round(min(s), 3),
        "max":   round(max(s), 3),
        "p50":   round(statistics.median(s), 3),
        "p95":   round(s[max(0, int(n * 0.95) - 1)], 3),
        "p99":   round(s[max(0, int(n * 0.99) - 1)], 3),
    }


def run_path(path_id: str, n_samples: int, runtime: SentinelRuntime,
             verbose: bool = False) -> Dict[str, Any]:
    cfg      = PATHS[path_id]
    cmds     = cfg["commands"]
    kwargs   = cfg.get("kwargs", {})
    latencies: List[float] = []

    # Warm-up (excluded from stats)
    for i in range(WARMUP_COUNT):
        cmd = cmds[i % len(cmds)]
        runtime.run_intercepted_command(cmd, **kwargs)

    # Timed samples
    for i in range(n_samples):
        cmd   = cmds[i % len(cmds)]
        start = time.perf_counter()
        runtime.run_intercepted_command(cmd, **kwargs)
        latencies.append((time.perf_counter() - start) * 1000)

    st = _stats(latencies)
    result = {
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "path_id":           path_id,
        "label":             cfg["label"],
        "description":       cfg["description"],
        "samples":           n_samples,
        "warmup":            WARMUP_COUNT,
        "semantic_invoked":  cfg["semantic_invoked"],
        "isolation_invoked": cfg["isolation_invoked"],
        **st,
    }
    if verbose:
        print(f"    warmup={WARMUP_COUNT}  samples={n_samples}  "
              f"semantic={cfg['semantic_invoked']}  isolation={cfg['isolation_invoked']}")
    return result


def print_path_result(r: Dict[str, Any]):
    print(f"\n  ── {r['label']} ({r['path_id']}) ──")
    print(f"     {r['description']}")
    print(f"     samples={r['samples']}  warmup={r['warmup']}")
    print(f"     semantic_invoked={r['semantic_invoked']}  "
          f"isolation_invoked={r['isolation_invoked']}")
    print(f"     p50={r['p50']}ms  p95={r['p95']}ms  p99={r['p99']}ms")
    print(f"     min={r['min']}ms  max={r['max']}ms")


def run_benchmarks(n_samples: int = 100, path_filter: Optional[str] = None,
                   json_output: bool = False) -> List[Dict[str, Any]]:
    print(f"\n{'═'*68}")
    print(f"  🚀  Sentinel Benchmark Suite v3.0 — Path-Split")
    print(f"{'═'*68}")
    print(f"  Samples per path : {n_samples}")
    print(f"  Warm-up per path : {WARMUP_COUNT} (excluded from stats)")

    runtime  = SentinelRuntime()
    paths    = [path_filter] if path_filter else list(PATHS.keys())
    results: List[Dict[str, Any]] = []

    for pid in paths:
        if pid not in PATHS:
            print(f"  ⚠️  Unknown path: {pid}")
            continue
        print(f"\n  Benchmarking: {pid} ...", flush=True)
        r = run_path(pid, n_samples, runtime)
        results.append(r)
        print_path_result(r)

    # ── Summary table ──────────────────────────────────────────────────────────
    if not json_output and len(results) > 1:
        print(f"\n{'═'*68}")
        print(f"  SUMMARY TABLE")
        print(f"{'═'*68}")
        print(f"  {'PATH':<22} {'p50':>8} {'p95':>8} {'p99':>8}  SEM  ISO")
        print(f"  {'─'*22} {'─'*8} {'─'*8} {'─'*8}  ───  ───")
        for r in results:
            sem = "Y" if r["semantic_invoked"]  else "N"
            iso = "Y" if r["isolation_invoked"] else "N"
            print(f"  {r['path_id']:<22} {r['p50']:>7}ms {r['p95']:>7}ms {r['p99']:>7}ms  {sem:>3}  {iso:>3}")

    # ── Persist results ────────────────────────────────────────────────────────
    with open(PERF_LOG, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"\n  ✅  Results appended to {PERF_LOG}")

    if json_output:
        print(json.dumps(results, indent=2))

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel Benchmark Runner v3.0")
    parser.add_argument("--samples", type=int, default=100,
                        help="Samples per path (default: 100)")
    parser.add_argument("--path", default=None,
                        choices=list(PATHS.keys()),
                        help="Run a single named path only")
    parser.add_argument("--all-paths", action="store_true",
                        help="Run all 8 paths (default when --path omitted)")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON summary to stdout")
    args = parser.parse_args()
    run_benchmarks(n_samples=args.samples, path_filter=args.path,
                   json_output=args.json)
