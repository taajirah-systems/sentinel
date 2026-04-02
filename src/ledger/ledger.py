"""
Sentinel Ledger — Authoritative append-only accounting and governance logs.

This module manages the low-level file writes for all system events.
Records are NEVER modified or deleted — only appended to the audit log.
"""

import os
import json
import fcntl
from pathlib import Path
from datetime import datetime, timezone

# Use the absolute path to ensure ledger files are stored in a predictable location
# REDIRECTION: Added support for isolated pilot runs via environment variable
LEDGER_DIR = Path(os.getenv("SENTINEL_LEDGER_DIR", "/Users/taajirah_systems/sentinel/ledger"))
LEDGER_DIR.mkdir(parents=True, exist_ok=True)

# Authorization & Accounting Logs
ACCOUNTING_LOG   = LEDGER_DIR / "accounting.jsonl"    # The master event stream
ORACLE_LOG       = LEDGER_DIR / "oracle_rates.jsonl"  # Exchange rate snapshots
COMPLIANCE_LOG   = LEDGER_DIR / "governance.jsonl"    # Compliance and admin overrides
INTEGRITY_LOG    = LEDGER_DIR / "integrity_events.jsonl" # State-machine violations
WALLETS_CACHE    = LEDGER_DIR / "wallets.json"        # Derived state cache


def _append(path: Path, record: dict) -> None:
    """Atomically append a JSON record to a JSONL file."""
    record["_written_at"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def write_accounting_event(record: dict) -> None:
    """Log an authoritative accounting event (allocation, spend, hold, etc)."""
    _append(ACCOUNTING_LOG, record)


def write_oracle_rate(record: dict) -> None:
    """Log a snapshot of service-credit exchange rates."""
    _append(ORACLE_LOG, record)


def write_compliance_event(record: dict) -> None:
    """Log a governance change or administrative override to the audit trail."""
    _append(COMPLIANCE_LOG, record)


def write_integrity_event(record: dict) -> None:
    """Log an authoritative integrity violation (invalid state transition, etc)."""
    _append(INTEGRITY_LOG, record)


def read_wallets() -> dict:
    """Read the current reconciled wallet state cache."""
    if not WALLETS_CACHE.exists():
        return {}
    with open(WALLETS_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_wallets(wallets: dict) -> None:
    """Persist reconciled wallet state (DERIVED CACHE)."""
    tmp = WALLETS_CACHE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(wallets, f, indent=2, ensure_ascii=False)
        fcntl.flock(f, fcntl.LOCK_UN)
    tmp.replace(WALLETS_CACHE)


def iter_accounting_events():
    """Generator to stream all authoritative accounting events from disk."""
    if not ACCOUNTING_LOG.exists():
        return
        
    with open(ACCOUNTING_LOG, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
