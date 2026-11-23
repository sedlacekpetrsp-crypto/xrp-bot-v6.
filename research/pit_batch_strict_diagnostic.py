"""Fail-closed, non-trading PIT batch diagnostic (PAPER research only).

A late observation is quarantined per row, not allowed to suppress valid rows.
No assumption that source publication time equals first observable time.
"""
from datetime import datetime, timezone

def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc)

def audit_batch(events, decision_at, min_latency_seconds=0):
    """Return (eligible, rejected) without generating trading signals.

    Every event must have event_id, published_at, first_seen_at.
    Eligible iff published <= first_seen AND first_seen + latency < decision.
    Duplicate identifiers are quarantined (including the first occurrence).
    """
    from datetime import timedelta
    decision = _utc(decision_at)
    if not isinstance(min_latency_seconds, (int, float)) or isinstance(min_latency_seconds, bool):
        raise ValueError("invalid latency")
    import math
    if not math.isfinite(min_latency_seconds) or min_latency_seconds < 0:
        raise ValueError("invalid latency")
    rows = list(events)
    ids = [row.get("event_id") if isinstance(row, dict) else None for row in rows]
    duplicated = {key for key in ids if key is not None and ids.count(key) > 1}
    accepted, rejected = [], []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("event_id"), str) or not row["event_id"].strip():
            rejected.append((row, "invalid_identity")); continue
        if row["event_id"] in duplicated:
            rejected.append((row, "duplicate_identity")); continue
        try:
            published, seen = _utc(row["published_at"]), _utc(row["first_seen_at"])
        except (KeyError, ValueError, TypeError, OverflowError):
            rejected.append((row, "invalid_timestamp")); continue
        if published > seen:
            rejected.append((row, "impossible_provenance")); continue
        try:
            ready = seen + timedelta(seconds=min_latency_seconds)
        except OverflowError:
            rejected.append((row, "latency_overflow")); continue
        if not ready < decision:
            rejected.append((row, "not_yet_available")); continue
        accepted.append(row)
    return accepted, rejected
