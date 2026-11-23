"""Fail-closed G1 label-maturity preflight (PAPER diagnostics only).

A decision's 14-day outcome cannot be scored until the full forward horizon
is observable. Fold membership is determined by decision time, not outcome time.
This module does not fetch data or execute a performance backtest.
"""
from datetime import datetime, timedelta, timezone


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware datetime values")
    return value.astimezone(timezone.utc)


def maturity_mask(decision_times, observation_cutoff, horizon_days=14):
    """Return maturity flags; reject non-monotonic grids and invalid horizons.

    Cutoff is the last *verified observable* timestamp, not wall-clock now.
    Equality counts as mature. Excluded/unlabeled observations must be handled
    separately; this function never treats immature labels as negatives.
    """
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or horizon_days <= 0:
        raise ValueError("horizon_days must be a positive integer")
    cutoff = _utc(observation_cutoff)
    previous = None
    flags = []
    for raw in decision_times:
        t = _utc(raw)
        if previous is not None and t <= previous:
            raise ValueError("decision grid must be strictly increasing")
        previous = t
        flags.append(t + timedelta(days=horizon_days) <= cutoff)
    return flags


def fold_maturity_counts(decision_times, fold_ids, observation_cutoff, horizon_days=14):
    """Summarize mature/immature rows per fold, preserving original fold IDs."""
    times = list(decision_times)
    folds = list(fold_ids)
    if len(times) != len(folds):
        raise ValueError("decision_times and fold_ids lengths differ")
    flags = maturity_mask(times, observation_cutoff, horizon_days)
    result = {}
    for fold, mature in zip(folds, flags):
        if not isinstance(fold, (str, int)) or isinstance(fold, bool):
            raise ValueError("fold IDs must be strings or integers")
        key = fold
        if key not in result:
            result[key] = {"mature": 0, "immature": 0}
        result[key]["mature" if mature else "immature"] += 1
    return result
