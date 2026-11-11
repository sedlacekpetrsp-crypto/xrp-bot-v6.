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
    trade_id: int | None = None

    def __post_init__(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() != timedelta(0):
            raise ValueError("Trade timestamp must be timezone-aware UTC")
        if not isinstance(self.price, Decimal) or not self.price.is_finite() or self.price <= 0:
            raise ValueError("Trade price must be a finite positive Decimal")
        if self.trade_id is not None and (type(self.trade_id) is not int or self.trade_id < 0):
            raise ValueError("trade_id must be a nonnegative integer")


def ordered_trades(trades: Iterable[Trade]) -> list[Trade]:
    """Order a single venue/symbol stream; reject ambiguous identity/order.

    Anonymous legacy fixtures are supported only at distinct timestamps.
    Native IDs resolve legitimate timestamp ties. IDs must be unique and
    increasing with event time; missing IDs are a separate coverage concern.
    """
    rows = list(trades)
    identified = [t.trade_id is not None for t in rows]
    if any(identified) and not all(identified):
        raise ValueError("mixed identified and anonymous trades")
    rows.sort(key=lambda t: (t.timestamp, t.trade_id if t.trade_id is not None else -1))
    if all(identified):
        if any(a.trade_id >= b.trade_id for a, b in zip(rows, rows[1:])):
            raise ValueError("duplicate or time-inconsistent trade IDs")
    elif any(a.timestamp == b.timestamp for a, b in zip(rows, rows[1:])):
        raise ValueError("ambiguous same-timestamp trades without IDs")
    return rows


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
    A caller MUST verify completeness independently before interpreting outcome=0.
    Trades later than as_of are ignored to prevent future-data leakage.
    """
    return label_touch(decision_at, trades, as_of, horizon=HORIZON, ratio=RISK_RATIO)


def label_touch(decision_at: datetime, trades: Iterable[Trade], as_of: datetime,
                *, horizon: timedelta, ratio: Decimal) -> Label:
    """Shared raw-touch label primitive, not a prediction or execution model.

    Outcomes 0 still require independent coverage QA. Early positives must not
    enter evaluation until the full target horizon matures (selection bias).
    For timestamp ties, native IDs determine the first reference trade. The
    protocol's open decision boundary excludes all trades exactly at decision.
    """
    if horizon <= timedelta(0) or not ratio.is_finite() or ratio <= 0 or ratio == 1:
        raise ValueError("positive horizon and finite non-unit positive ratio required")
    if decision_at.tzinfo is None or decision_at.utcoffset() != timedelta(0):
        raise ValueError("decision_at must be UTC")
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of must be UTC")
    if as_of < decision_at:
        raise ValueError("as_of precedes decision_at")
    deadline = decision_at + horizon
    rows = ordered_trades(x for x in trades if decision_at <= x.timestamp <= min(as_of, deadline))
    ref = next((x for x in rows if decision_at <= x.timestamp <= decision_at + MAX_REFERENCE_DELAY), None)
    if ref is None:
        return Label(decision_at, None, None, deadline, None, None, "missing_reference")
    threshold = ref.price * ratio
    hit = next((x for x in rows if decision_at < x.timestamp <= deadline
                and (x.price <= threshold if ratio < 1 else x.price >= threshold)), None)
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
