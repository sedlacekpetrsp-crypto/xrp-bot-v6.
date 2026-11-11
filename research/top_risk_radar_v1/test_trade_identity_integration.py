"""Regression tests for real archive schema defects, with synthetic values."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from research.top_risk_radar_v1.binance_spot_trades import epoch_to_utc, parse_spot_trades_csv
from research.top_risk_radar_v1.coverage_qa import audit_coverage
from research.top_risk_radar_v1.label_events import Trade, label_decision

T = datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc)


def row(id=1, price="1", qty="1", quote="1", timestamp="1735689900000001", maker="true"):
    return f"{id},{price},{qty},{quote},{timestamp},{maker},true"


@pytest.mark.parametrize("price", ["Infinity", "-Infinity", "NaN", "sNaN", "0", "-1"])
def test_nonfinite_or_nonpositive_trade_rejected(price):
    with pytest.raises(ValueError):
        Trade(T, Decimal(price))


@pytest.mark.parametrize("fields", [{"qty": "0"}, {"quote": "NaN"}, {"qty": "Infinity"}, {"maker": "yes"}])
def test_invalid_archive_fields_rejected(fields):
    with pytest.raises(ValueError):
        parse_spot_trades_csv([row(**fields)])


@pytest.mark.parametrize("second_id", [1, 0])
def test_duplicate_or_decreasing_ids_rejected(second_id):
    with pytest.raises(ValueError, match="trade ID"):
        parse_spot_trades_csv([row(), row(id=second_id)])


def test_parser_preserves_identity_and_same_timestamp_hit():
    trades = parse_spot_trades_csv([row(), row(id=2, price="0.8")])
    assert [t.trade_id for t in trades] == [1, 2]
    # Same timestamp is later than decision; exchange IDs establish first reference.
    result = label_decision(T, reversed(trades), T + timedelta(seconds=1))
    assert result.reference_price == Decimal("1")
    assert result.outcome == 1
    assert result.first_hit_at == T + timedelta(microseconds=1)


def test_observed_archive_boolean_case():
    # Actual first row of checksum-verified 2024-01-02 archive, not a made-up format.
    raw = "576925834,0.62950000,596.00000000,375.18200000,1704153600439,False,True"
    trade, = parse_spot_trades_csv([raw])
    assert trade.trade_id == 576925834
    assert trade.price == Decimal("0.62950000")
    assert trade.timestamp == datetime(2024, 1, 2, 0, 0, 0, 439000, tzinfo=timezone.utc)


def test_anonymous_reference_tie_abstains_by_exception():
    with pytest.raises(ValueError, match="ambiguous"):
        label_decision(T, [Trade(T, Decimal("1")), Trade(T, Decimal("0.8"))], T)


def test_exact_decision_boundary_excludes_all_tied_hits():
    trades = [Trade(T, Decimal("1"), 1), Trade(T, Decimal("0.8"), 2)]
    assert label_decision(T, trades, T).outcome is None


@pytest.mark.parametrize("ids,status", [([1, 2, 3], "contiguous_ids"),
                                        ([1, 3, 4], "missing_ids"),
                                        ([1, 1, 2], "invalid_ids"),
                                        ([1, None, 3], "invalid_ids")])
def test_identity_aware_coverage(ids, status):
    trades = [Trade(T + timedelta(seconds=s), Decimal("1"), id)
              for s, id in zip([1, 1, 60], ids)]
    report = audit_coverage(T, trades, T + timedelta(seconds=60), horizon=timedelta(seconds=60))
    assert report.duplicate_timestamps == 1  # count retained as diagnostics
    assert report.identity_status == status
    assert report.acceptable == (status == "contiguous_ids")


@pytest.mark.parametrize("timestamp", ["1735689600010866", "99999999999999999"])
def test_epoch_conversion_preserves_every_microsecond(timestamp):
    expected = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=int(timestamp))
    assert epoch_to_utc(timestamp) == expected


def test_coverage_rejects_cutoff_before_decision():
    with pytest.raises(ValueError, match="precedes"):
        audit_coverage(T, [], T - timedelta(microseconds=1))
