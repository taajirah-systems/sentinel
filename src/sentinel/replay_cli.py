"""
Sentinel Decision Replay CLI v2.0
===================================
Full forensic reconstruction of a Sentinel trace from JSONL audit log.
Includes: stage timing deltas, semantic summary, redaction summary,
          failure-trace rendering, runtime-denial detail, approval stages,
          --json machine-readable output.

Usage:
  python3 src/sentinel/replay_cli.py <trace-id>
  python3 src/sentinel/replay_cli.py <trace-id> --json
  python3 src/sentinel/replay_cli.py <trace-id> --verbose
"""
import json
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS_DIR      = Path(__file__).resolve().parent
AUDIT_LOG_PATH = _THIS_DIR / "logs" / "audit_structured.jsonl"
_LEGACY_PATH   = Path("./src/sentinel/logs/audit_structured.jsonl")

# ── Stage ordering for delta calculation ──────────────────────────────────────
_STAGE_ORDER = [
    "intake", "normalization", "redaction", "policy_evaluation",
    "semantic_audit", "isolation_wrap", "execution_result",
    "runtime_denial", "approval_pending", "approval_logged",
    "final_decision", "execution_decision",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_log() -> Path:
    return AUDIT_LOG_PATH if AUDIT_LOG_PATH.exists() else _LEGACY_PATH

def _load_events(trace_id: str) -> List[Dict[str, Any]]:
    log = _resolve_log()
    if not log.exists():
        return []
    events = []
    with open(log, "r", encoding="utf-8") as f:
        for line in f:
            try:
                ev = json.loads(line)
                if ev.get("correlation_id") == trace_id:
                    events.append(ev)
            except json.JSONDecodeError:
                continue
    return sorted(events, key=lambda e: e.get("timestamp", ""))

def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

def _delta_ms(ts1: str, ts2: str) -> Optional[float]:
    a, b = _parse_ts(ts1), _parse_ts(ts2)
    if a and b:
        return round((b - a).total_seconds() * 1000, 2)
    return None

def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    return str(v)

def _truncate(s: str, n: int = 120) -> str:
    if len(s) > n:
        return s[:n-1] + "…"
    return s

# ── Rendering ─────────────────────────────────────────────────────────────────

def _render_header(events: List[Dict], trace_id: str):
    first = events[0]
    print(f"\n{'━'*70}")
    print(f"  🛡️  Sentinel Decision Replay v2.0")
    print(f"{'━'*70}")
    print(f"  Trace ID         : {trace_id}")
    print(f"  Schema version   : {first.get('schema_version', '—')}")
    print(f"  Sentinel version : {first.get('sentinel_version', '—')}")
    print(f"  Policy version   : {first.get('policy_version', '—')}")
    print(f"  Agent            : {first.get('agent_id', '—')}")
    print(f"  Original input   : {_fmt(first.get('input'))}")
    print(f"  Events captured  : {len(events)}")
    ts_first = first.get("timestamp", "")
    ts_last  = events[-1].get("timestamp", "") if len(events) > 1 else ts_first
    span     = _delta_ms(ts_first, ts_last)
    print(f"  Total span       : {span}ms" if span is not None else "  Total span       : —")
    print(f"{'━'*70}")


def _render_timeline(events: List[Dict]):
    print(f"\n  {'TIME':12}  {'Δ(ms)':>7}  {'STAGE':<22}  {'DECISION':<16}  REASON")
    print(f"  {'─'*12}  {'─'*7}  {'─'*22}  {'─'*16}  {'─'*30}")
    prev_ts = None
    for ev in events:
        ts_str  = ev.get("timestamp", "")
        ts_disp = ts_str.split("T")[-1][:12] if "T" in ts_str else ts_str[:12]
        stage   = ev.get("stage", ev.get("event_type", "?"))
        dec     = _fmt(ev.get("decision"))
        reason  = ev.get("reason") or ""
        reason_s = _truncate(reason, 40)
        delta   = _delta_ms(prev_ts, ts_str) if prev_ts else 0.0
        delta_s = f"{delta:>6.1f}" if delta is not None else "     —"
        # Visual flags
        flag = ""
        if stage == "runtime_denial":
            flag = "  ⛔"
        elif stage in ("approval_pending", "approval_logged"):
            flag = "  👤"
        elif ev.get("metadata", {}).get("sandbox_denial"):
            flag = "  🔒"
        print(f"  {ts_disp:12}  {delta_s:>7}  {stage:<22}  {dec:<16}  {reason_s}{flag}")
        prev_ts = ts_str


def _render_stage_artifacts(events: List[Dict]):
    print(f"\n{'─'*70}")
    print(f"  DECISION ARTIFACTS (per stage)")
    print(f"{'─'*70}")
    for ev in events:
        stage = ev.get("stage", ev.get("event_type", "?"))
        dec   = ev.get("decision")
        missing_indicator = ""

        print(f"\n  ▸ {stage}")
        print(f"    decision        : {_fmt(dec)}")
        print(f"    reason          : {_truncate(_fmt(ev.get('reason')), 100)}")

        norm =ev.get("normalized_input")
        if norm is not None:
            print(f"    normalized_input: {_truncate(_fmt(norm), 100)}")

        # Redaction summary
        if stage == "redaction":
            meta = ev.get("metadata", {})
            redacted = meta.get("redacted", False)
            count    = meta.get("count", 0)
            print(f"    redacted        : {redacted}  (fields: {count})")

        # Semantic summary
        if stage == "semantic_audit":
            meta = ev.get("metadata", {})
            print(f"    risk_score      : {meta.get('risk_score', '—')}")
            print(f"    model_used      : {meta.get('model', '—')}")
            rationale = str(meta.get("rationale", "") or "")
            if rationale:
                print(f"    rationale       : {_truncate(rationale, 100)}")

        # Metadata keys
        meta = ev.get("metadata") or {}
        skip_keys = {"redacted", "count", "risk_score", "model", "rationale"}
        for k, v in meta.items():
            if k in skip_keys:
                continue
            val = _truncate(str(v), 110)
            print(f"    {k:<20}: {val}")


def _render_isolation(events: List[Dict]):
    isol = next((e for e in events if e.get("stage") == "isolation_wrap"), None)
    if not isol:
        return
    im = isol.get("metadata", {})
    print(f"\n{'─'*70}")
    print(f"  ISOLATION LAYER")
    print(f"{'─'*70}")
    print(f"  Backend      : {im.get('backend', '—')}")
    print(f"  Shell op     : {im.get('shell_operator', '—')}")
    wrapped = str(im.get("wrapped_argv", "—"))
    print(f"  Wrapped argv : {_truncate(wrapped, 120)}")
    # Extract SBPL snippet
    profile = str(im.get("wrapped_argv", ""))
    if "deny" in profile:
        lines = [l.strip() for l in profile.split("\\n") if "deny" in l]
        for l in lines[:5]:
            print(f"  SBPL deny    : {l}")


def _render_runtime_denial(events: List[Dict]):
    rtd = next((e for e in events if e.get("stage") == "runtime_denial"), None)
    if not rtd:
        return
    rm = rtd.get("metadata", {})
    print(f"\n{'─'*70}")
    print(f"  ⛔ RUNTIME DENIAL — Sandbox rejected syscall at execution")
    print(f"{'─'*70}")
    print(f"  Exit code    : {rm.get('returncode', '?')}")
    print(f"  Denial type  : {rm.get('denial_type', '—')}")
    print(f"  Backend      : {rm.get('backend', '—')}")
    stderr = str(rm.get("stderr_snippet", ""))
    if stderr:
        print(f"  Stderr       : {_truncate(stderr, 100)}")
    print(f"  Note: This is an OS-level rejection, not a policy block.")
    print(f"        The process WAS spawned under sandbox-exec but its syscall was denied.")


def _render_approval(events: List[Dict]):
    pending = [e for e in events if e.get("stage") == "approval_pending"]
    logged  = [e for e in events if e.get("stage") == "approval_logged"]
    if not pending and not logged:
        return
    print(f"\n{'─'*70}")
    print(f"  👤 APPROVAL STAGE")
    print(f"{'─'*70}")
    for ev in pending:
        print(f"  Status   : PENDING — awaiting operator decision")
        print(f"  Input    : {_fmt(ev.get('input'))}")
    for ev in logged:
        meta = ev.get("metadata", {})
        print(f"  Actor    : {meta.get('actor_id', '—')}")
        print(f"  Decision : {_fmt(ev.get('decision'))}")
        print(f"  Reason   : {_fmt(ev.get('reason'))}")
        print(f"  Override : {meta.get('override_reason', '—')}")


def _render_final_decision(events: List[Dict]):
    final = next(
        (e for e in reversed(events) if e.get("stage") == "final_decision"), None
    ) or next(
        (e for e in reversed(events) if e.get("stage") == "execution_decision"), None
    )
    print(f"\n{'━'*70}")
    print(f"  FINAL DECISION")
    print(f"{'━'*70}")
    if final:
        dec     = final.get("decision", "unknown")
        verdict = ("✅ ALLOW" if dec == "allow"
                   else "⛔ RUNTIME_DENIED" if dec == "runtime_denied"
                   else "❌ BLOCK")
        rm = final.get("metadata", {})
        print(f"  Verdict    : {verdict}")
        print(f"  Reason     : {_fmt(final.get('reason'))}")
        print(f"  Risk score : {rm.get('risk_score', '—')}")
        print(f"  Returncode : {rm.get('returncode', '—')}")
        print(f"  Isolation  : {rm.get('isolation', '—')}")
        if rm.get("sandbox_denial"):
            print(f"  ⚠️  Note: Policy allowed but sandbox denied at runtime.")
    else:
        print(f"  (no final_decision event found in this trace)")


def _render_failure_warning(events: List[Dict]):
    """Warn if trace is incomplete or contains failure markers."""
    stages_seen = {e.get("stage") for e in events}
    expected_stages = {"intake", "final_decision"}
    missing = expected_stages - stages_seen
    if missing:
        print(f"\n{'─'*70}")
        print(f"  ⚠️  INCOMPLETE TRACE")
        print(f"{'─'*70}")
        for s in missing:
            print(f"  Missing stage: {s}")
        print(f"  This trace may represent a mid-execution failure.")
        print(f"  Check audit log for surrounding context.")


# ── Main entry point ──────────────────────────────────────────────────────────

def replay_trace(trace_id: str, verbose: bool = False, json_mode: bool = False):
    events = _load_events(trace_id)
    if not events:
        print(f"\n❌  No events found for trace ID: {trace_id}")
        if not _resolve_log().exists():
            print(f"   Audit log not found at {_resolve_log()}")
        return

    if json_mode:
        print(json.dumps(events, indent=2, default=str))
        return

    _render_header(events, trace_id)
    _render_timeline(events)
    _render_failure_warning(events)
    _render_stage_artifacts(events)
    _render_isolation(events)
    _render_runtime_denial(events)
    _render_approval(events)
    _render_final_decision(events)

    print(f"\n{'━'*70}")
    print(f"  Replay complete — trace ID: {trace_id}")
    print(f"{'━'*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel Decision Replay CLI v2.0")
    parser.add_argument("trace_id", help="The correlation/trace ID to replay")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output (dump raw events)")
    args = parser.parse_args()
    replay_trace(args.trace_id, verbose=args.verbose, json_mode=args.json)
