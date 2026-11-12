from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from research.top_risk_radar_v1.census_touch_bound import evaluate

T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)

def flat(hours, o=D("1")):
    return [(T0 + timedelta(hours=h), (o, o, o)) for h in range(hours)]

def test_intrahour_wick_counts_as_touch_close_would_not():
    rows = dict(flat(24 * 40))
    t = T0 + timedelta(hours=5)
    rows[t] = (D("1"), D("1.31"), D("0.79"))  # wick both ways, close stays 1
    r = evaluate(sorted(rows.items()))
    assert r["growth_positive_decisions"] >= 1 and r["risk_positive_decisions"] >= 1
    assert r["grouped_risk_episodes_14d"] == 1

def test_no_touch_flat_series():
    r = evaluate(flat(24 * 40))
    assert r["growth_positive_decisions"] == 0 and r["risk_positive_decisions"] == 0
    assert r["matured_decisions"] == 10

def test_missing_hour_excludes_decision():
    rows = [x for x in flat(24 * 40) if x[0] != T0 + timedelta(hours=3)]
    r = evaluate(rows)
    assert r["excluded_missing_data"] == 1
