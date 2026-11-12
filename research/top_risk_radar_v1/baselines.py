"""Train-only constant-event-rate baseline M0 for synthetic PAPER radar QA.

M0 is a fitted reference probability, NOT an OOS result. Labels are explicit
0/1, and must have matured before the fold's training cutoff. No market I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from collections.abc import Sequence

BASELINE_VERSION = "radar-m0-train-only-v1"
HORIZON_HOURS = {"growth": 720, "downside": 336}


@dataclass(frozen=True)
class LabelRow:
    decision_at: datetime
    label_available_at: datetime
    label: int | None


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def fit_m0(train: Sequence[LabelRow], *, target: str, test_start: datetime) -> dict:
    """Fit M0 using only labels mature strictly before the first test decision.

    Reject duplicate decisions, contradictory label timestamps, and unknown
    types. Missing/unmatured labels are excluded, never treated as zero.
    """
    if target not in HORIZON_HOURS:
        raise ValueError("unknown_target")
    cutoff = _utc(test_start)
    horizon = timedelta(hours=HORIZON_HOURS[target])
    seen: set[datetime] = set()
    values: list[int] = []
    for row in train:
        decision = _utc(row.decision_at)
        available = _utc(row.label_available_at)
        if decision in seen:
            raise ValueError("duplicate_decision")
        seen.add(decision)
        if row.label is not None and (type(row.label) is not int or row.label not in (0, 1)):
            raise ValueError("invalid_label")
        if available < decision + horizon:
            raise ValueError("premature_label_availability")
        if decision >= cutoff:
            continue
        if row.label is not None and decision + horizon < cutoff and available < cutoff:
            values.append(row.label)
    if not values:
        return {"version": BASELINE_VERSION, "target": target, "status": "insufficient_train",
                "n_train": 0, "probability": None}
    probability = math.fsum(values) / len(values)
    return {"version": BASELINE_VERSION, "target": target, "status": "fitted_train_only",
            "n_train": len(values), "probability": probability}
