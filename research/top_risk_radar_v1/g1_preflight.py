"""Fail-closed composition of G1 decision-grid QA and fixed fold contract.

Synthetic/unit-only adapter. The eventual manual G1 runner must call this
entry point rather than the permissive legacy fold function. No I/O or fitting.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from .g1_decision_input import validate_g1_decisions
from .g1_calendar_coverage import require_complete_g1_decision_days
from .g1_fold_contract import g1_calendar_folds
from .walkforward import Fold


def validated_g1_folds(decisions: Sequence[datetime], *, as_of: datetime) -> list[Fold]:
    """Validate the full 00:05 UTC grid before constructing embargoed folds."""
    validate_g1_decisions(decisions)
    return g1_calendar_folds(decisions, as_of=as_of)


def complete_g1_folds(
    decisions: Sequence[datetime], *, as_of: datetime,
    coverage_start: datetime, coverage_end: datetime,
) -> list[Fold]:
    """Fail closed on missing days in the declared inclusive audit interval.

    The caller must supply independently fixed coverage bounds; deriving them
    from observed rows would silently hide missing leading/trailing dates.
    This function does not impute missing market observations or score models.
    """
    require_complete_g1_decision_days(
        decisions, start=coverage_start, end=coverage_end,
    )
    return validated_g1_folds(decisions, as_of=as_of)
