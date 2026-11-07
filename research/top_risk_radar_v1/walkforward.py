"""Leakage-safe calendar folds for XRP radar research. No training, trading or I/O."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

@dataclass(frozen=True)
class Fold:
    test_year: int
    train_indices: tuple[int,...]
    test_indices: tuple[int,...]
    excluded_unmatured: tuple[int,...]

def expanding_calendar_folds(decisions: Sequence[datetime], *,
                             label_horizon: timedelta,
                             as_of: datetime,
                             first_train_year: int = 2018,
                             first_test_year: int = 2022,
                             last_test_year: int = 2026) -> list[Fold]:
    """Require full label maturity before training or evaluation.

    The test year's training window ends at Jan 1 of that year, with a
    horizon-sized purge so no training label reaches into test time.
    Only chronological calendar splits; no fitting/calibration performed.
    """
    if label_horizon <= timedelta(0):
        raise ValueError("positive label horizon required")
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of must be UTC")
    if not first_train_year < first_test_year <= last_test_year:
        raise ValueError("invalid year range")
    for d in decisions:
        if d.tzinfo is None or d.utcoffset() != timedelta(0):
            raise ValueError("decisions must be UTC")
    folds=[]
    for year in range(first_test_year,last_test_year+1):
        start=datetime(year,1,1,tzinfo=timezone.utc)
        end=datetime(year+1,1,1,tzinfo=timezone.utc)
        train=tuple(i for i,d in enumerate(decisions)
                    if first_train_year <= d.year < year
                    and d+label_horizon <= start
                    and d+label_horizon <= as_of)
        test=tuple(i for i,d in enumerate(decisions)
                   if start <= d < end and d+label_horizon <= as_of)
        excluded=tuple(i for i,d in enumerate(decisions)
                       if start <= d < end and d+label_horizon > as_of)
        folds.append(Fold(year,train,test,excluded))
    return folds
