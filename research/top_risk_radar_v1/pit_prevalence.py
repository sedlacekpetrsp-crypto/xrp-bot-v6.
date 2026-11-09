"""Strict point-in-time descriptive prevalence for XRP radar research.

Requires a verifiable publication/availability timestamp for each label.
This is not a predictive validation or a trading backtest.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware datetimes")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class PITObservation:
    decision_at: datetime
    label_available_at: datetime | None
    growth: bool | None
    downside: bool | None


def pit_historical_prevalence(
    train: Sequence[PITObservation],
    test_start: datetime,
    *,
    horizon_days: int,
    target: str,
) -> dict:
    """Descriptive prior from known, mature AND demonstrably available labels.

    Unknown availability is excluded (not guessed from the event horizon).
    All timestamps/labels are validated, including rows that cannot be used.
    """
    if target not in ("growth", "downside"):
        raise ValueError("unknown target")
    if type(horizon_days) is not int or horizon_days <= 0:
        raise ValueError("horizon_days must be a positive integer")
    # Prevent silently applying the 14-day downside window to 30-day growth,
    # or vice versa. Both labels have fixed pre-registered horizons.
    required_horizon = {"growth": 30, "downside": 14}[target]
    if horizon_days != required_horizon:
        raise ValueError(f"{target} requires horizon_days={required_horizon}")
    cutoff = _utc(test_start)
    try:
        horizon = timedelta(days=horizon_days)
    except OverflowError as exc:
        raise ValueError("horizon_days out of range") from exc

    eligible: list[bool] = []
    seen: set[datetime] = set()
    for row in train:
        decision = _utc(row.decision_at)
        if decision in seen:
            raise ValueError("duplicate decision timestamp")
        seen.add(decision)
        available = None if row.label_available_at is None else _utc(row.label_available_at)
        if available is not None and available < decision:
            raise ValueError("label cannot be available before its decision")
        if type(row.growth) not in (bool, type(None)) or type(row.downside) not in (bool, type(None)):
            raise TypeError("event labels must be bool or None")
        label = getattr(row, target)
        # A negative event label cannot be known before its entire event
        # horizon has elapsed. A positive label may be known at first hit.
        # Fail closed rather than accepting an impossible early negative.
        if label is False and available is not None and available - decision < horizon:
            raise ValueError("negative label available before horizon maturity")
        if label is None or available is None or decision >= cutoff:
            continue
        # Subtraction avoids datetime overflow near datetime.min/max.
        if cutoff - decision >= horizon and available <= cutoff:
            eligible.append(label)

    if not eligible:
        return {"status": "insufficient_train", "n": 0, "rate": None}
    return {"status": "descriptive_pit_baseline", "n": len(eligible), "rate": sum(eligible) / len(eligible)}
