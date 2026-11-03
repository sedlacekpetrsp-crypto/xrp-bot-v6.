"""Research-only SHORT signal evaluator. Never places PAPER or live orders."""
from datetime import datetime, timezone

STRATEGY = "WHALE_SHORT_RSI_SHADOW"
RSI_MIN, RSI_MAX = 40.0, 60.0

def evaluate(candidate):
    """Return an immutable-style diagnostic for prospective observation."""
    if candidate.get("strategy") != "FIB_618_786":
        return None
    if str(candidate.get("side", "")).upper() != "SHORT":
        return None
    details = candidate.get("technical_details") or {}
    hourly = details.get("1h") or {}
    try:
        rsi = float(hourly["rsi"])
        entry = float(candidate["candidate_entry"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (RSI_MIN <= rsi <= RSI_MAX and entry > 0):
        return None
    return {
        "strategy": STRATEGY,
        "candidate_key": candidate.get("candidate_key"),
        "symbol": candidate.get("symbol"),
        "side": "SHORT",
        "entry_reference": entry,
        "rsi_1h": rsi,
        "status": "SHADOW_ONLY_NO_ORDERS",
        "observed_at": candidate.get("first_seen_at"),
    }
