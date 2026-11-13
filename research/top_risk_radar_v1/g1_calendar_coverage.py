"""G1 calendar coverage gate: report missing UTC decision dates before OOS scoring.

Pure deterministic QA only; no market data, model fitting or performance run.
A sparse decision list can pass the timestamp validator yet bias evaluation
if missing dates silently disappear. A caller must resolve omissions explicitly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from .g1_decision_input import validate_g1_decisions


def missing_g1_decision_days(
    decisions: Sequence[datetime], *, start: datetime, end: datetime
) -> tuple[datetime, ...]:
    """Return missing 00:05 UTC dates in inclusive [start, end].

    Bounds must themselves be canonical G1 decision timestamps. No dates are
    synthesized into the dataset; this is a fail-closed reporting primitive.
    """
    validate_g1_decisions((start, end) if start < end else (start,))
    if end < start:
        raise ValueError("end precedes start")
    validate_g1_decisions(decisions)
    expected_count = (end.date() - start.date()).days + 1
    if any(d < start or d > end for d in decisions):
        raise ValueError("decision outside audited interval")
    observed = set(decisions)
    return tuple(start + timedelta(days=i) for i in range(expected_count)
                 if start + timedelta(days=i) not in observed)


def require_complete_g1_decision_days(
    decisions: Sequence[datetime], *, start: datetime, end: datetime
) -> None:
    """Block scoring until omissions have been audited and resolved."""
    missing = missing_g1_decision_days(decisions, start=start, end=end)
    if missing:
        raise ValueError(
            f"G1 calendar coverage incomplete: {len(missing)} missing UTC days; "
            f"first={missing[0].isoformat()}"
        )
