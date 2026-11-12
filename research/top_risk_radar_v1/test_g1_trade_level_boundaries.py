"""G1 pre-freeze trade-level PIT boundaries: synthetic only, no performance data."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from research.top_risk_radar_v1.label_events import Trade, label_decision

T = datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc)
H = timedelta(hours=336)


def tr(seconds, price, trade_id):
    return Trade(T + timedelta(seconds=seconds), Decimal(price), trade_id)


def test_reference_is_first_actual_trade_not_minute_open_at_decision():
    rows = [tr(17, "1.00", 100), tr(18, "0.79", 101)]
    label = label_decision(T, rows, T + H)
    assert label.reference_at == T + timedelta(seconds=17)
    assert label.reference_price == Decimal("1.00")
    assert label.first_hit_at == T + timedelta(seconds=18)
    assert label.outcome == 1


def test_earlier_price_low_cannot_be_used_as_post_reference_hit():
    rows = [tr(-1, "0.60", 99), tr(17, "1.00", 100), tr(18, "0.99", 101)]
    label = label_decision(T, rows, T + H)
    assert label.outcome == 0
    assert label.first_hit_at is None


def test_trade_after_reference_window_is_not_valid_reference():
    label = label_decision(T, [tr(61, "1.00", 100)], T + H)
    assert label.status == "missing_reference"
    assert label.outcome is None


def test_trade_at_reference_window_end_is_valid():
    label = label_decision(T, [tr(60, "1.00", 100)], T + H)
    assert label.reference_at == T + timedelta(seconds=60)
    assert label.outcome == 0


def test_positive_touch_at_horizon_boundary_is_included():
    rows = [tr(1, "1.00", 100), Trade(T + H, Decimal("0.80"), 101)]
    label = label_decision(T, rows, T + H)
    assert label.outcome == 1
    assert label.first_hit_at == T + H


def test_touch_after_horizon_is_excluded():
    rows = [tr(1, "1.00", 100), Trade(T + H + timedelta(microseconds=1), Decimal("0.70"), 101)]
    label = label_decision(T, rows, T + H + timedelta(days=1))
    assert label.outcome == 0


def test_early_positive_is_known_but_maturity_must_be_enforced_by_training_gate():
    rows = [tr(1, "1.00", 100), tr(2, "0.70", 101)]
    label = label_decision(T, rows, T + timedelta(seconds=3))
    assert label.outcome == 1
    assert label.deadline_at == T + H
    assert label.deadline_at > T + timedelta(seconds=3)


def test_without_hit_negative_cannot_be_labeled_before_maturity():
    rows = [tr(1, "1.00", 100), tr(2, "0.99", 101)]
    label = label_decision(T, rows, T + H - timedelta(microseconds=1))
    assert label.outcome is None
    assert label.status == "unmatured"


def test_same_timestamp_hit_after_reference_uses_native_trade_id():
    rows = [tr(10, "0.80", 102), tr(10, "1.00", 101)]
    label = label_decision(T, rows, T + H)
    assert label.outcome == 1
    assert label.reference_price == Decimal("1.00")


def test_same_timestamp_hit_before_reference_is_not_a_future_touch():
    rows = [tr(10, "0.80", 101), tr(10, "1.00", 102)]
    label = label_decision(T, rows, T + H)
    assert label.reference_price == Decimal("0.80")
    assert label.outcome == 0


@pytest.mark.parametrize("price", ["NaN", "Infinity", "0"])
def test_invalid_reference_trade_rejected(price):
    with pytest.raises(ValueError):
        Trade(T, Decimal(price), 100)
