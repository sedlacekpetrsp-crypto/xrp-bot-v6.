from datetime import datetime, timedelta, timezone
from research.top_risk_radar_v1.census_exact_1m import evaluate

T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)

def flat(days):
    return [(T0 + timedelta(minutes=k), 1.0, 1.0, 1.0, 5) for k in range(days * 1440)]

def test_flat_no_labels_and_maturity():
    r = evaluate(flat(3), risk_h=24, growth_h=24)
    assert r["matured_decisions"] == 2 and r["risk_positive_decisions"] == 0

def test_minute_wick_hits_and_window_starts_at_0005():
    rows = flat(3)
    k = 1440 + 2  # day1 00:02: inside day0 window [00:05, +24h), before day1 decision
    rows[k] = (rows[k][0], 1.0, 1.0, 0.79, 5)
    r = evaluate(rows, risk_h=24, growth_h=24)
    assert r["risk_positive_decisions"] == 1
    rows = flat(3); k = 1440 + 10  # day1 00:10: only day1 window
    rows[k] = (rows[k][0], 1.0, 1.0, 0.79, 5)
    assert evaluate(rows, risk_h=24, growth_h=24)["risk_positive_decisions"] == 1

def test_no_trade_excludes():
    rows = flat(3)
    rows[5] = (rows[5][0], 1.0, 1.0, 1.0, 0)
    r = evaluate(rows, risk_h=24, growth_h=24)
    assert r["excluded"]["no_trade_in_first_60s"] == 1

def test_missing_minute_excludes():
    rows = flat(3); del rows[100]
    r = evaluate(rows, risk_h=24, growth_h=24)
    assert r["excluded"]["missing_minutes_in_horizon"] == 1
