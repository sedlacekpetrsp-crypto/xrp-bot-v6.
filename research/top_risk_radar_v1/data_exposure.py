"""Audit-only data exposure ledger for XRP radar research (PAPER).

Records whether a period remains eligible as a genuinely untouched holdout.
No model fitting, performance scoring, trading or network I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Sequence

LEVELS = {"none": 0, "prevalence-viewed": 1, "tuned": 2}


@dataclass(frozen=True)
class Exposure:
    start: datetime
    end: datetime
    level: str
    evidence: str


def _utc(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamps must be timezone-aware UTC")


def validate_exposures(rows: Sequence[Exposure]) -> None:
    """Fail closed on missing provenance, overlaps and malformed intervals."""
    previous_end = None
    for row in rows:
        _utc(row.start)
        _utc(row.end)
        if row.start >= row.end:
            raise ValueError("interval must have positive duration")
        if row.level not in LEVELS:
            raise ValueError("unknown exposure level")
        if not isinstance(row.evidence, str) or not row.evidence.strip():
            raise ValueError("evidence reference required, including for 'none'")
        if previous_end is not None and row.start < previous_end:
            raise ValueError("exposure intervals overlap or are unsorted")
        previous_end = row.end


def untouched_holdout(rows: Sequence[Exposure], start: datetime, end: datetime) -> bool:
    """Only fully covered, explicitly unexposed intervals qualify.

    Gaps are NOT assumed clean. An observed prevalence, even without tuning,
    disqualifies a period from being described as completely untouched.
    """
    _utc(start)
    _utc(end)
    if start >= end:
        raise ValueError("holdout interval must have positive duration")
    validate_exposures(rows)
    cursor = start
    for row in rows:
        if row.end <= cursor:
            continue
        if row.start > cursor:
            return False
        if row.level != "none":
            return False
        cursor = min(end, row.end)
        if cursor == end:
            return True
    return False
