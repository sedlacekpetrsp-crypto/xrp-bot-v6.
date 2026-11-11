"""Trade-level growth labels, cross-horizon separation and shared references."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from research.early_growth_radar_v1.label_events import label_decision as growth
from research.top_risk_radar_v1.label_events import Trade, label_decision as risk

T = datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc)


def tr(days, price, id):
    return Trade(T + timedelta(days=days), Decimal(price), id)


@pytest.mark.parametrize("price,outcome", [("1.30", 1), ("1.299999", 0), ("1.31", 1)])
def test_growth_threshold_is_exact(price, outcome):
    result = growth(T, [tr(0, "1", 1), tr(30, price, 2)], T + timedelta(days=30))
    assert result.outcome == outcome
    assert result.deadline_at == T + timedelta(hours=720)


def test_post_deadline_touch_excluded():
    rows = [tr(0, "1", 1), Trade(T + timedelta(days=30, microseconds=1), Decimal("2"), 2)]
    assert growth(T, rows, T + timedelta(days=31)).outcome == 0


def test_no_growth_negative_before_full_horizon():
    result = growth(T, [tr(0, "1", 1)], T + timedelta(days=30) - timedelta(microseconds=1))
    assert result.outcome is None
    assert result.status == "unmatured"


def test_future_touch_and_future_reference_invisible():
    assert growth(T, [tr(0, "1", 1), tr(1, "2", 2)], T).outcome is None
    assert growth(T, [Trade(T + timedelta(seconds=1), Decimal("1"), 1)], T).status == "missing_reference"


@pytest.mark.parametrize("delay,status", [(60, "unmatured"), (60.000001, "missing_reference")])
def test_reference_delay_boundary(delay, status):
    result = growth(T, [Trade(T + timedelta(seconds=delay), Decimal("1"), 1)], T + timedelta(days=1))
    assert result.status == status


@pytest.mark.parametrize("growth_day,risk_day", [(1, 2), (2, 1)])
def test_both_events_preserve_order_and_reference(growth_day, risk_day):
    prices = sorted([(growth_day, "1.3"), (risk_day, "0.8")])
    rows = [tr(0, "1", 1)] + [tr(d, p, i + 2) for i, (d, p) in enumerate(prices)]
    g = growth(T, rows, T + timedelta(days=30))
    r = risk(T, rows, T + timedelta(days=30))
    assert g.outcome == r.outcome == 1
    assert g.reference_at == r.reference_at == T
    assert g.reference_price == r.reference_price == Decimal("1")
    assert g.first_hit_at == T + timedelta(days=growth_day)
    assert r.first_hit_at == T + timedelta(days=risk_day)


def test_downside_after_fourteen_days_is_not_risk_event():
    rows = [tr(0, "1", 1), tr(15, "0.7", 2), tr(29, "1.3", 3)]
    assert risk(T, rows, T + timedelta(days=30)).outcome == 0
    assert growth(T, rows, T + timedelta(days=30)).outcome == 1


def test_growth_same_timestamp_hit_uses_exchange_ids():
    ts = T + timedelta(microseconds=1)
    rows = [Trade(ts, Decimal("1.3"), 2), Trade(ts, Decimal("1"), 1)]
    assert growth(T, rows, ts).outcome == 1


def test_mature_negative_still_requires_coverage():
    assert growth(T, [tr(0, "1", 1)], T + timedelta(days=30)).status == "negative_requires_coverage_qa"
