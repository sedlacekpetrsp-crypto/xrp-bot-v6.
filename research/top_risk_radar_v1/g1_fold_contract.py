"""Fail-closed G1 fold entry point. Synthetic/unit research only; no model fitting or I/O.

The generic expanding_calendar_folds retains a zero-embargo default for legacy
callers. G1 must never use that default implicitly.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from .walkforward import Fold, expanding_calendar_folds

G1_HORIZON = timedelta(days=14)
G1_EMBARGO = timedelta(days=14)


def g1_calendar_folds(decisions: Sequence[datetime], *, as_of: datetime) -> list[Fold]:
    """Apply frozen G1 label maturity + embargo, without optional overrides."""
    return expanding_calendar_folds(
        decisions,
        label_horizon=G1_HORIZON,
        embargo=G1_EMBARGO,
        as_of=as_of,
        first_train_year=2018,
        first_test_year=2022,
        last_test_year=2026,
    )
