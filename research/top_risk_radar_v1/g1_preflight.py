"""Fail-closed composition of G1 decision-grid QA and fixed fold contract.

Synthetic/unit-only adapter. The eventual manual G1 runner must call this
entry point rather than the permissive legacy fold function. No I/O or fitting.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from .g1_decision_input import validate_g1_decisions
from .g1_fold_contract import g1_calendar_folds
from .walkforward import Fold


def validated_g1_folds(decisions: Sequence[datetime], *, as_of: datetime) -> list[Fold]:
    """Validate the full 00:05 UTC grid before constructing embargoed folds."""
    validate_g1_decisions(decisions)
    return g1_calendar_folds(decisions, as_of=as_of)
