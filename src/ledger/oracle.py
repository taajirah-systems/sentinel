"""
Sentinel JOULE Oracle — Real-time valuation of 1 JOULE in ZAR/USD.

Polls provider pricing and FX rates every 15 minutes.
Falls back to cached snapshot if network is unavailable.
"""

import json
import time
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .ledger import write_oracle_rate, LEDGER_DIR

# ── Default provider costs (ZAR per 1M tokens) ──────────────────────────────
# These are manually configured baselines — oracle updates them from live FX.
# Costs in USD per 1M tokens (from provider pricing pages):
_PROVIDER_USD_PER_1M = {
    "google-1":   0.075,   # Gemini Flash
    "google-2":   0.075,   # Gemini Flash (second key)
    "google-pro": 3.50,    # Gemini Pro
    "openai":     5.00,    # GPT-4o
    "local_gpu":  0.01,    # RTX 4090 amortised + Eskom electricity
    "unknown":    0.075,   # Default to cheapest cloud
}

CACHE_FILE = LEDGER_DIR / "oracle_cache.json"
REFRESH_INTERVAL_SEC = 900  # 15 minutes

_cache: dict = {}
_lock = threading.Lock()


def _fetch_usd_to_zar() -> float:
    """Fetch live USD/ZAR rate from a free public API."""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return float(data["rates"]["ZAR"])
    except Exception:
        # Fallback to last known rate if network fails
        return _cache.get("usd_to_zar", 18.50)


def _build_snapshot(usd_to_zar: float) -> dict:
    """
    Build a valuation snapshot. 
    The Oracle is authoritative for compute cost estimation but advisory to treasury policy.
    """
    provider_rates = {
        provider: {
            "cost_per_1m_tokens_usd": usd_cost,
            "cost_per_1m_tokens_zar": round(usd_cost * usd_to_zar, 4),
        }
        for provider, usd_cost in _PROVIDER_USD_PER_1M.items()
    }
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "usd_to_zar": usd_to_zar,
        "jul_to_zar": 1.00,        # 1 JUL mapped to 1 ZAR (Internal Administrative Index)
        "jul_to_usd": round(1.0 / usd_to_zar, 6),
        "provider_rates": provider_rates,
    }


def _refresh() -> None:
    global _cache
    usd_to_zar = _fetch_usd_to_zar()
    snapshot = _build_snapshot(usd_to_zar)
    with _lock:
        _cache = snapshot
    # Persist to disk cache and audit log
    with open(CACHE_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)
    write_oracle_rate(snapshot)
    print(f"[ORACLE] Refreshed — 1 USD = {usd_to_zar:.2f} ZAR | "
          f"1 JUL = {snapshot['jul_to_usd']:.6f} USD")


def _load_cache() -> None:
    """Load last known snapshot from disk on startup."""
    global _cache
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            _cache = json.load(f)


def _background_refresh() -> None:
    while True:
        try:
            _refresh()
        except Exception as e:
            print(f"[ORACLE] Refresh error: {e}")
        time.sleep(REFRESH_INTERVAL_SEC)


def start_oracle() -> None:
    """Start the background oracle refresh thread."""
    _load_cache()
    if not _cache:
        _refresh()  # Blocking first fetch
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print("[ORACLE] Started — refreshing every 15 minutes")


def get_current_rate(provider: str = "unknown") -> dict:
    """
    Return current cost info for a given provider.

    Returns:
        dict with keys: cost_per_1m_tokens_zar, cost_per_1m_tokens_usd
    """
    with _lock:
        rates = _cache.get("provider_rates", {})
    if provider in rates:
        return rates[provider]
    return rates.get("unknown", {
        "cost_per_1m_tokens_zar": 1.35,
        "cost_per_1m_tokens_usd": 0.075,
    })


def get_jul_to_zar() -> float:
    """Return current JOULE → ZAR conversion rate."""
    with _lock:
        return _cache.get("jul_to_zar", 1.00)


def get_jul_to_usd() -> float:
    """Return current JOULE → USD conversion rate."""
    with _lock:
        return _cache.get("jul_to_usd", 0.054)
