"""XRP downside event labeling. Research only; no orders, no network access."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

UTC = timezone.utc
HORIZON = timedelta(hours=336)
MAX_REFERENCE_DELAY = timedelta(seconds=60)
RISK_RATIO = Decimal("0.80")


@dataclass(frozen=True)
class Trade:
    timestamp: datetime
    price: Decimal

    def __post_init__(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() != timedelta(0):
            raise ValueError("Trade timestamp must be timezone-aware UTC")
        if self.price <= 0:
            raise ValueError("Trade price must be positive")


@dataclass(frozen=True)
class Label:
    decision_at: datetime
    reference_at: datetime | None
    reference_price: Decimal | None
    deadline_at: datetime
    first_hit_at: datetime | None
    outcome: int | None
    status: str


def label_decision(decision_at: datetime, trades: Iterable[Trade], as_of: datetime) -> Label:
    """Only label a negative after the complete 336h window has matured.

    The input must contain all eligible trades for the venue through the window.
    A caller MUST verify completeness independently before interpreting outcome=0.\n    Trades later than as_of are ignored to prevent future-data leakage.
    """
    if decision_at.tzinfo is None or decision_at.utcoffset() != timedelta(0):
        raise ValueError("decision_at must be UTC")
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of must be UTC")
    if as_of < decision_at:\n        raise ValueError("as_of precedes decision_at")\n    deadline = decision_at + HORIZON
    rows = sorted((x for x in trades if x.timestamp <= as_of), key=lambda x: x.timestamp)
    ref = next((x for x in rows if decision_at <= x.timestamp <= decision_at + MAX_REFERENCE_DELAY), None)
    if ref is None:
        return Label(decision_at, None, None, deadline, None, None, "missing_reference")
    hit = next((x for x in rows if ref.timestamp < x.timestamp <= deadline and x.price <= ref.price * RISK_RATIO), None)
    if hit is not None:
        return Label(decision_at, ref.timestamp, ref.price, deadline, hit.timestamp, 1, "positive")
    if as_of < deadline:
        return Label(decision_at, ref.timestamp, ref.price, deadline, None, None, "unmatured")
    return Label(decision_at, ref.timestamp, ref.price, deadline, None, 0, "negative_requires_coverage_qa")


def point_in_time_eligible(published_at: datetime, received_at: datetime, decision_at: datetime) -> bool:
    for t in (published_at, received_at, decision_at):
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            raise ValueError("All times must be UTC")
    return max(published_at, received_at) <= decision_at
