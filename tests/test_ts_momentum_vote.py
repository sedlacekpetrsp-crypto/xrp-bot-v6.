"""Mechanika TS momentum vote backtestu na syntetických datech (není důkaz ziskovosti)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from research.ts_momentum_vote import run

D0 = date(2021, 1, 1)


def mk(closes, opens=None):
    out = []
    for i, c in enumerate(closes):
        o = opens[i] if opens else c
        ts = int(datetime(D0.year, D0.month, D0.day, tzinfo=timezone.utc).timestamp() * 1000) + i * 86_400_000
        out.append({"ts": ts, "open": o, "high": max(o, c), "low": min(o, c), "close": c})
    return out


def d(i):
    return D0 + timedelta(days=i)


def test_target_weight_counts_positive_horizons():
    cbd = {d(0): 100.0, d(400 - 365): 50.0, d(400 - 182): 200.0, d(400 - 91): 50.0, d(400 - 30): 200.0, d(400): 100.0}
    assert run.target_weight(cbd, d(400)) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        run.target_weight({d(10): 1.0}, d(10))


def test_uptrend_full_weight_and_ledger_sums_to_equity():
    closes = [100 * 1.001 ** i for i in range(800)]
    b = mk(closes)
    start, end = date(2022, 3, 1), date(2022, 8, 31)
    tr, cv = run.simulate(b, start, end, mult=1, equity=1000.0)
    assert len(tr) == 1 and tr[0]["weight_held"] == 1.0 and tr[0]["exit_reason"] == "period_end"
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[end] - 1000.0)
    for t in tr:
        assert t["net_pnl"] == pytest.approx(t["gross_pnl"] - t["fees"])


def test_downtrend_zero_weight_no_trades_flat_equity():
    closes = [1000 * 0.999 ** i for i in range(800)]
    b = mk(closes)
    tr, cv = run.simulate(b, date(2022, 3, 1), date(2022, 8, 31), mult=1, equity=1000.0)
    assert tr == [] and all(v == 1000.0 for v in cv.values())


def test_regime_switch_records_and_no_lookahead():
    # roste 600 dní, pak prudce padá: váha musí klesat až s close předchozího dne, ne dřív
    closes = [100 * 1.002 ** i for i in range(600)] + [100 * 1.002 ** 599 * 0.98 ** k for k in range(1, 200)]
    b = mk(closes)
    start, end = date(2022, 6, 1), date(2023, 2, 28)
    tr, cv = run.simulate(b, start, end, mult=1, equity=1000.0)
    assert len(tr) >= 2
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[end] - 1000.0)
    for t in tr:
        assert date.fromisoformat(t["exit_day"]).day == 1 or t["exit_reason"] == "period_end"
    # první změna nastane až 1. den měsíce PO prvním poklesu (pád začíná d(600) = 2022-08-24)
    first_change = date.fromisoformat(tr[0]["exit_day"])
    assert first_change >= date(2022, 9, 1)


def test_partial_weight_and_cost_scaling():
    closes = [100 * 1.001 ** i for i in range(800)]
    b = mk(closes)
    s, e = date(2022, 3, 1), date(2022, 8, 31)
    t1, c1 = run.simulate(b, s, e, mult=1, equity=1000.0, horizons=(30, 91, 182, 365))
    t3, c3 = run.simulate(b, s, e, mult=3, equity=1000.0)
    assert c3[e] < c1[e] and t3[0]["fees"] > 2.5 * t1[0]["fees"]


def test_weekly_rebalances_on_mondays():
    closes = [100 * 1.001 ** i for i in range(800)]
    b = mk(closes)
    assert run.is_rebalance_day(date(2023, 1, 2), date(2023, 1, 1), True)      # pondělí
    assert not run.is_rebalance_day(date(2023, 1, 3), date(2023, 1, 1), True)
    assert run.is_rebalance_day(date(2023, 2, 1), date(2023, 1, 1), False)
    tr, cv = run.simulate(b, date(2022, 3, 1), date(2022, 8, 31), mult=1, equity=1000.0, weekly=True)
    assert sum(t["net_pnl"] for t in tr) == pytest.approx(cv[date(2022, 8, 31)] - 1000.0)
