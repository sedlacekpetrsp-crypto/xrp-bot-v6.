"""Mechanika funding carry (syntetická data — NENÍ důkaz ziskovosti)."""
from datetime import date, timedelta

import pytest

from research.funding_carry import run as fc


def _series(n=40, px=lambda i: 100.0, rate=lambda i: 0.0001, high_mult=lambda i: 1.0, d0=date(2023, 1, 1)):
    spot, perp, fund = {}, {}, []
    for i in range(-8, n):
        d = d0 + timedelta(days=i)
        p = px(i)
        bar = {"ts": fc.day_start_ms(d), "open": p, "high": p * high_mult(i), "low": p, "close": p}
        spot[d] = dict(bar)
        perp[d] = dict(bar)
        for h in (0, 8, 16):
            fund.append({"ts": fc.day_start_ms(d) + h * 3_600_000 + 5, "interval_h": 8.0, "rate": rate(i)})
    return {"spot": spot, "perp": perp, "funding": fund}, d0, d0 + timedelta(days=n - 1)


def test_flat_price_earns_funding_minus_costs_and_ledger_sums():
    s, a, b = _series()
    eps, curve, final = fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
    assert len(eps) == 1 and eps[0]["exit_reason"] == "period_end"
    assert eps[0]["funding"] > 0 and eps[0]["costs"] > 0
    assert sum(e["net_pnl"] for e in eps) == pytest.approx(final - fc.SLEEVE, abs=1e-4)
    assert eps[0]["net_pnl"] == pytest.approx(eps[0]["funding"] - eps[0]["costs"], abs=1e-3)
    # entry at open of day 2 (signal from close day 1) => the 00:00 event of entry day is not received
    assert eps[0]["entry_date"] == (a + timedelta(days=1)).isoformat()


def test_below_threshold_no_trade():
    s, a, b = _series(rate=lambda i: 0.00005)  # ~5.5 % p.a.
    eps, _, final = fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
    assert eps == [] and final == fc.SLEEVE


def test_negative_funding_exit_signal():
    s, a, b = _series(rate=lambda i: 0.0001 if i < 15 else -0.0003)
    eps, _, final = fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
    assert eps[0]["exit_reason"] == "signal"
    assert sum(e["net_pnl"] for e in eps) == pytest.approx(final - fc.SLEEVE, abs=1e-4)


def test_price_rise_triggers_rebalance_and_stays_delta_neutral():
    s, a, b = _series(px=lambda i: 100.0 * (1.03 ** max(0, i)))
    eps, curve, final = fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
    assert eps[0]["rebalances"] >= 1 and eps[0]["liquidated"] == 0
    # delta-neutral: P/L ≈ funding − costs even though price rose ~3x
    assert eps[0]["net_pnl"] == pytest.approx(eps[0]["funding"] - eps[0]["costs"], rel=0.05, abs=1.0)


def test_liquidation_on_spike():
    s, a, b = _series(high_mult=lambda i: 3.0 if i == 10 else 1.0)
    eps, _, final = fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
    assert eps[0]["liquidated"] == 1 and eps[0]["exit_reason"] == "liquidation"
    assert eps[0]["net_pnl"] < -0.4 * fc.SLEEVE
    assert sum(e["net_pnl"] for e in eps) == pytest.approx(final - fc.SLEEVE, abs=1e-4)


def test_costs_scale_with_multiplier():
    s, a, b = _series()
    e1, _, f1 = fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
    e3, _, f3 = fc.simulate_sleeve(s, "X", a, b, 3, 0.10)
    assert e3[0]["costs"] == pytest.approx(3 * e1[0]["costs"], rel=0.02) and f3 < f1


def test_missing_bar_raises():
    s, a, b = _series()
    del s["perp"][a + timedelta(days=5)]
    with pytest.raises(ValueError):
        fc.simulate_sleeve(s, "X", a, b, 1, 0.10)
