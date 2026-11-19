"""PAPER-only K9 matched-hour benchmark: deterministic, data-free boundary audit.

The phase-B random benchmark uses start = index.get_indexer([t.floor('h')])[0].
A valid partial first hour has no floor('h') row; this must not silently
remove its eligible control minutes. Audit candidate selection independently.
No returns, orders, or historical backtests.
"""
from __future__ import annotations

import pandas as pd


def hour_candidate_positions(index: pd.DatetimeIndex, signal_time: pd.Timestamp, horizon: int) -> list[int]:
    """Return candidate positions in the same *UTC calendar hour* with full horizon.

    Caller must independently apply PIT matching, exclusions, and price validity.
    Fail closed for unsorted, duplicate, naive, or non-minute timestamps.
    """
    if horizon < 1:
        raise ValueError("horizon must be positive")
    if index.tz is None or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("index must be sorted, unique and timezone-aware")
    utc = index.tz_convert("UTC")
    if len(utc) and not (utc == utc.floor("min")).all():
        raise ValueError("index must contain whole minutes")
    signal = pd.Timestamp(signal_time)
    if signal.tzinfo is None:
        raise ValueError("signal must be timezone-aware")
    signal = signal.tz_convert("UTC")
    if signal not in utc:
        return []
    hour = signal.floor("h")
    return [
        i for i, t in enumerate(utc)
        if t.floor("h") == hour and t != signal and i + horizon < len(utc)
        and utc[i + horizon] == t + pd.Timedelta(minutes=horizon)
    ]
