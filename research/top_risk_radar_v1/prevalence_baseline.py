"""Leakage-safe historical prevalence baselines for event labels.

This is NOT a trained prediction model. Unknown labels must be excluded, never
converted to negatives. Train dates must mature before test starts.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timedelta
from typing import Sequence

@dataclass(frozen=True)
class Observation:
    decision_at: datetime
    growth: bool | None
    downside: bool | None

def historical_prevalence(train: Sequence[Observation], test_start: datetime,
                          *, horizon_days: int, target: str) -> dict:
    if target not in ("growth","downside"): raise ValueError("unknown target")
    if horizon_days<=0: raise ValueError("invalid horizon")
    eligible=[getattr(o,target) for o in train
              if o.decision_at+timedelta(days=horizon_days)<=test_start
              and getattr(o,target) is not None]
    if not eligible:
        return {"status":"insufficient_train","n":0,"rate":None}
    return {"status":"descriptive_baseline","n":len(eligible),
            "rate":sum(eligible)/len(eligible)}
