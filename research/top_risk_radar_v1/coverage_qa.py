"""Deterministic trade-feed QA for XRP radar research. No network/trading."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Sequence
from research.top_risk_radar_v1.label_events import Trade, ordered_trades

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
    identity_status: str = "unverified"
    missing_trade_ids: int | None = None

def audit_coverage(decision_at: datetime, trades: Sequence[Trade], as_of: datetime,
                   horizon: timedelta = timedelta(days=14),
                   max_gap: timedelta = timedelta(minutes=5)) -> CoverageReport:
    """Conservative heuristic, NOT proof of complete feed or exchange uptime.

    Timestamp ties are legitimate when unique native trade IDs prove order.
    Identified streams must have contiguous IDs. Anonymous streams retain the
    legacy heuristic but cannot prove identity; tied anonymous rows fail closed.
    Exchange trade frequency may naturally be sparse; failing is preferable
    to silently treating unknown outcomes as negatives.
    """
    if decision_at.tzinfo is None or decision_at.utcoffset() != timedelta(0):
        raise ValueError("decision_at must be UTC")
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of must be UTC")
    if horizon <= timedelta(0) or max_gap <= timedelta(0):
        raise ValueError("horizon and max_gap must be positive")
    if as_of < decision_at:
        raise ValueError("as_of precedes decision_at")
    deadline = decision_at + horizon
    rows = sorted((t for t in trades if decision_at <= t.timestamp <= deadline and t.timestamp <= as_of), key=lambda t: t.timestamp)
    times = [t.timestamp for t in rows]
    duplicates = sum(a == b for a,b in zip(times,times[1:]))
    identity_status = "unverified"
    missing_ids = None
    identity_ok = duplicates == 0
    if any(t.trade_id is not None for t in rows):
        try:
            identified_rows = ordered_trades(rows)
            missing_ids = sum(b.trade_id - a.trade_id - 1
                              for a, b in zip(identified_rows, identified_rows[1:]))
            identity_ok = missing_ids == 0
            identity_status = "contiguous_ids" if identity_ok else "missing_ids"
        except ValueError:
            identity_ok = False
            identity_status = "invalid_ids"
    gaps = [(b-a).total_seconds() for a,b in zip(times,times[1:])]
    ref_ok = bool(times and times[0] <= decision_at + timedelta(seconds=60))
    end_ok = bool(times and times[-1] >= deadline - max_gap and as_of >= deadline)
    worst = max(gaps) if gaps else None
    ok = ref_ok and end_ok and identity_ok and bool(gaps) and worst <= max_gap.total_seconds()
    reason = "heuristic_pass_requires_independent_source_qa" if ok else "incomplete_or_suspicious_trade_coverage"
    return CoverageReport(times[0] if times else None,times[-1] if times else None,len(times),duplicates,worst,ref_ok,end_ok,ok,reason,identity_status,missing_ids)


def audit_label_coverage(label, trades: Sequence[Trade], as_of: datetime,
                         max_gap: timedelta = timedelta(minutes=5)) -> CoverageReport:
    """Coverage QA bound to the label's own horizon (fail-closed).

    The generic default horizon (14 days) matches only the downside target;
    a +30%/720h growth negative audited with that default would pass on
    14 days of data. Deriving the horizon from ``label.deadline_at`` removes
    that cross-horizon footgun.
    """
    horizon = label.deadline_at - label.decision_at
    return audit_coverage(label.decision_at, trades, as_of, horizon=horizon, max_gap=max_gap)
