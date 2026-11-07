"""Deterministic trade-feed QA for XRP radar research. No network/trading."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Sequence
from research.top_risk_radar_v1.label_events import Trade

@dataclass(frozen=True)
class CoverageReport:
    first_at: datetime | None
    last_at: datetime | None
    trades: int
    duplicate_timestamps: int
    max_gap_seconds: float | None
    reference_covered: bool
    window_end_covered: bool
    acceptable: bool
    reason: str

def audit_coverage(decision_at: datetime, trades: Sequence[Trade], as_of: datetime,
                   horizon: timedelta = timedelta(days=14),
                   max_gap: timedelta = timedelta(minutes=5)) -> CoverageReport:
    """Conservative heuristic, NOT proof of complete feed or exchange uptime.

    Only accepts if records span reference and endpoint, have no duplicate
    timestamps, and no gaps > max_gap across the requested window.
    Exchange trade frequency may naturally be sparse; failing is preferable
    to silently treating unknown outcomes as negatives.
    """
    if decision_at.tzinfo is None or decision_at.utcoffset() != timedelta(0):
        raise ValueError("decision_at must be UTC")
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of must be UTC")
    if horizon <= timedelta(0) or max_gap <= timedelta(0):
        raise ValueError("horizon and max_gap must be positive")
    deadline = decision_at + horizon
    rows = sorted((t for t in trades if decision_at <= t.timestamp <= deadline and t.timestamp <= as_of), key=lambda t: t.timestamp)
    times = [t.timestamp for t in rows]
    duplicates = sum(a == b for a,b in zip(times,times[1:]))
    gaps = [(b-a).total_seconds() for a,b in zip(times,times[1:])]
    ref_ok = bool(times and times[0] <= decision_at + timedelta(seconds=60))
    end_ok = bool(times and times[-1] >= deadline - max_gap and as_of >= deadline)
    worst = max(gaps) if gaps else None
    ok = ref_ok and end_ok and duplicates == 0 and bool(gaps) and worst <= max_gap.total_seconds()
    reason = "heuristic_pass_requires_independent_source_qa" if ok else "incomplete_or_suspicious_trade_coverage"
    return CoverageReport(times[0] if times else None,times[-1] if times else None,len(times),duplicates,worst,ref_ok,end_ok,ok,reason)
