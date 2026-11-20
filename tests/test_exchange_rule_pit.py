from datetime import datetime, timezone, timedelta
import pytest
from research.exchange_rule_pit import RuleSnapshot, rule_asof, minimum_roundtrip_cost

T = datetime(2025, 1, 1, tzinfo=timezone.utc)
def snap(value="10", pub=T, cap=T, eff=T, symbol="XRPUSDT"):
    return RuleSnapshot("binance", symbol, "minNotional", value, pub, cap, eff, "sha256:test")

def query(items, at=T):
    return rule_asof(items, venue="binance", symbol="XRPUSDT",
                     rule="minNotional", decision_at=at)

def test_valid_evidence(): assert query([snap()])["status"] == "DATA_GO"
def test_future_capture_rejected(): assert query([snap(cap=T+timedelta(days=1))])["status"] == "DATA_NO_GO"
def test_future_effective_rejected(): assert query([snap(eff=T+timedelta(days=1))])["status"] == "DATA_NO_GO"
def test_future_publication_rejected(): assert query([snap(pub=T+timedelta(days=1),cap=T+timedelta(days=1))])["status"] == "DATA_NO_GO"
def test_wrong_symbol_rejected(): assert query([snap(symbol="BTCUSDT")])["status"] == "DATA_NO_GO"
def test_latest_effective_wins():
    assert query([snap("10",eff=T-timedelta(days=1)),snap("20")])["value"] == "20"
def test_conflict_fails_closed():
    assert query([snap("10"),snap("20")])["reason"] == "conflicting_rule_evidence"
def test_capture_before_publication_invalid():
    with pytest.raises(ValueError): query([snap(pub=T+timedelta(seconds=1))])
def test_naive_datetime_invalid():
    with pytest.raises(ValueError): query([snap()], datetime(2025,1,1))
def test_cost_floor(): assert minimum_roundtrip_cost("5","2") == 14
def test_negative_cost_invalid():
    with pytest.raises(ValueError): minimum_roundtrip_cost("-1","2")
def test_nan_cost_invalid():
    with pytest.raises(ValueError): minimum_roundtrip_cost("NaN","2")
