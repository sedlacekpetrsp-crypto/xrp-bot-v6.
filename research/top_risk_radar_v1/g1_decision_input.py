"""Strict daily G1 decision-grid validator; no market data, fitting or performance I/O.

Call before constructing G1 folds. Deliberately separate from the legacy
fold adapter, whose existing synthetic tests exercise arbitrary timestamps.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence


def validate_g1_decisions(decisions: Sequence[datetime]) -> None:
    """Fail closed on non-UTC, non-00:05, duplicate or out-of-order decisions.

    A missing calendar day is permitted here: data QA must separately report
    coverage and exclusion reasons rather than silently filling observations.
    """
    previous = None
    for index, decision in enumerate(decisions):
        if not isinstance(decision, datetime):
            raise ValueError(f"decision[{index}] must be a datetime")
        if decision.tzinfo is None or decision.utcoffset() != timedelta(0):
            raise ValueError(f"decision[{index}] must be UTC")
        if (decision.hour, decision.minute, decision.second, decision.microsecond) != (0, 5, 0, 0):
            raise ValueError(f"decision[{index}] must be exactly 00:05:00 UTC")
        if previous is not None and decision <= previous:
            raise ValueError(f"decision[{index}] is duplicate or out of order")
        previous = decision
