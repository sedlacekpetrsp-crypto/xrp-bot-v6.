"""Leakage-safe historical event-prevalence baseline (PAPER research only).

Descriptive prior, NOT a fitted prediction model or validated OOS result.
Unknown labels are excluded, never silently treated as negative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence


@dataclass(frozen=True)
class Observation:
    decision_at: datetime
    growth: bool | None
    downside: bool | None


def _utc(value: datetime) -> datetime:
    """Reject ambiguous naive timestamps and normalize offset-aware instants."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware datetimes")
    return value.astimezone(timezone.utc)


def historical_prevalence(
    train: Sequence[Observation],
    test_start: datetime,
    *,
    horizon_days: int,
    target: str,
) -> dict:
    """Rate among known labels fully mature by the first test decision.

    A decision exactly at test_start is never training data. Every timestamp
    is validated even for an unknown label; mixing naive/aware timestamps
    must fail closed rather than silently changing eligibility.
    """
    if target not in ("growth", "downside"):
        raise ValueError("unknown target")
    if not isinstance(horizon_days, int) or isinstance(horizon_days, bool) or horizon_days <= 0:
        raise ValueError("horizon_days must be a positive integer")
    cutoff = _utc(test_start)
    horizon = timedelta(days=horizon_days)
    eligible: list[bool] = []
    for row in train:
        decision = _utc(row.decision_at)
        label = getattr(row, target)
        if label is not None and type(label) is not bool:
            raise TypeError("event label must be bool or None")
        if decision < cutoff and cutoff - decision >= horizon and label is not None:
            eligible.append(label)
    if not eligible:
        return {"status": "insufficient_train", "n": 0, "rate": None}
    return {
        "status": "descriptive_baseline",
        "n": len(eligible),
        "rate": sum(eligible) / len(eligible),
    }
