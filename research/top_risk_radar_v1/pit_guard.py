"""Point-in-time availability guards for XRP radar research (PAPER only).

No trading, market-data downloads, model fitting or performance evaluation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; reject naive timestamps and malformed inputs."""
    if not isinstance(value, str):
        raise TypeError("timestamp must be an ISO-8601 string")
    if "T" not in value and "t" not in value and " " not in value:
        raise ValueError("timestamp must include a clock time, not a date alone")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("naive timestamp is forbidden")
    return dt.astimezone(timezone.utc)


def feature_is_available(record: Mapping[str, str], decision_time: str) -> bool:
    """True only when both publication AND collector receipt predate decision.

    Missing publication/receipt timestamps fail closed; a separately reviewed,
    versioned lag policy is needed before allowing those sources.
    """
    decision = parse_utc(decision_time)
    event = parse_utc(record["event_time"])
    published = parse_utc(record["source_published_at"])
    received = parse_utc(record["collector_received_at"])
    return event < decision and published <= decision and received <= decision


def label_is_mature(decision_time: str, cutoff: str, horizon_hours: int) -> bool:
    """Prevent incomplete negative labels; never infer maturity from an early hit."""
    from datetime import timedelta

    if type(horizon_hours) is not int or horizon_hours <= 0:
        raise ValueError("horizon_hours must be a positive integer")
    return parse_utc(decision_time) + timedelta(hours=horizon_hours) <= parse_utc(cutoff)
