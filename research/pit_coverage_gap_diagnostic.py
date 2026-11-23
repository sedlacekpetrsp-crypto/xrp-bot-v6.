"""PAPER-only data availability coverage diagnostic; never fills missing observations.

The expected grid must be predeclared independently of the observed feed.
This module does not establish archival authenticity or predict returns.
"""
from datetime import datetime, timezone
from math import isfinite


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware datetimes")
    return value.astimezone(timezone.utc)


def audit_coverage(expected_times, observations, decision_time):
    """Return missing, late and usable grid counts; fail closed on malformed inputs.

    observations: iterable of (event_time, first_available_at).
    Events not in the predeclared grid are rejected. Duplicate events are
    rejected even if one of the duplicates was late.
    """
    decision = _utc(decision_time)
    expected = [_utc(t) for t in expected_times]
    if expected != sorted(set(expected)):
        raise ValueError("expected grid must be sorted and unique")
    if any(t > decision for t in expected):
        raise ValueError("expected grid extends beyond decision")
    expected_set = set(expected)
    seen = {}
    for event, available in observations:
        event, available = _utc(event), _utc(available)
        if event not in expected_set:
            raise ValueError("event outside predeclared grid")
        if event in seen:
            raise ValueError("duplicate event")
        if available < event:
            raise ValueError("available_at precedes event")
        seen[event] = available
    missing = sum(t not in seen for t in expected)
    late = sum(t in seen and seen[t] >= decision for t in expected)
    usable = len(expected) - missing - late
    return {"expected": len(expected), "usable": usable, "missing": missing,
            "late": late, "coverage": usable / len(expected) if expected else None,
            "status": "EMPTY_GRID" if not expected else ("COMPLETE" if usable == len(expected) else "INCOMPLETE")}
