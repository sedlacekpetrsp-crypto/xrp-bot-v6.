"""Fail-closed point-in-time availability gate for PAPER research datasets.

Diagnostic only. No market access, returns, signals, or backtesting.
All timestamps are timezone-aware UTC; known_at is when a record became
available to the strategy, not when the underlying event occurred.
"""
from datetime import datetime, timezone


class PITError(ValueError):
    pass


def _utc(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PITError(f"{name}: timezone-aware datetime required")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise PITError(f"{name}: UTC required")
    return value.astimezone(timezone.utc)


def eligible(record, decision_at, *, required_fields=("event_at", "known_at")):
    """Return True only if evidence existed at decision time.

    Reject missing fields, non-UTC timestamps, publication before event,
    and future knowledge. An explicit provenance marker is mandatory.
    """
    if not isinstance(record, dict):
        raise PITError("record must be dict")
    # Caller-supplied fields may add requirements, never waive PIT timestamps.
    for field in ("event_at", "known_at", *required_fields):
        if field not in record:
            raise PITError(f"missing {field}")
    event = _utc(record["event_at"], "event_at")
    known = _utc(record["known_at"], "known_at")
    decision = _utc(decision_at, "decision_at")
    if not isinstance(record.get("provenance"), str) or not record["provenance"].strip():
        raise PITError("missing provenance")
    if known < event:
        raise PITError("known_at precedes event_at")
    return event <= decision and known <= decision


def audit(records, decision_at):
    """Count eligible/unavailable observations; fail on malformed evidence."""
    _utc(decision_at, "decision_at")  # validate even for an empty iterable
    accepted = unavailable = 0
    for record in records:
        if eligible(record, decision_at):
            accepted += 1
        else:
            unavailable += 1
    return {"eligible": accepted, "unavailable": unavailable}
