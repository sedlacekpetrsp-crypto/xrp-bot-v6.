"""Mechanika A2 ŠIROKÝ TREND na syntetických datech (ne důkaz výkonnosti)."""
from datetime import date, timedelta

import pytest

from research.broad_trend import run as R

START = date(2021, 1, 1)


def mk(sym, prices, start=START, highs=None, funding=None, first=None, last=None, qv=1e6):
    bars = {}
    for k, p in enumerate(prices):
        if p is None:
            continue
        h = highs[k] if highs else p
        bars[R.di(start + timedelta(days=k))] = (p, h, p, p, 1.0, qv)
    first = first or start
    last = last or start + timedelta(days=len(prices) - 1)
    s = R.Series(sym, bars, first, last, funding)
    return s


def monday_after(d):
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def trend(n, a=100.0, g=0.01):
    return [a * (1 + g) ** k for k in range(n)]


def wiggle(n, a=100.0, g=0.01, amp=0.02):
    return [a * (1 + g) ** k * (1 + amp * (1 if k % 2 else -1)) for k in range(n)]


def test_prefix_invariance_of_weights():
    up = wiggle(300)
    s1 = mk("AAAUSDT", up)
    r = R.di(monday_after(START + timedelta(days=200)))
    w1, _ = R.target_weights([s1], r, 50, "LS")
    alt = up[: r - R.di(START)] + [1.0] * (300 - (r - R.di(START)))
    s2 = mk("AAAUSDT", alt)
    w2, _ = R.target_weights([s2], r, 50, "LS")
    assert w1 == w2 and w1["AAAUSDT"] > 0


def test_signal_lo_ls_and_caps():
    up, dn = mk("UPUSDT", wiggle(300)), mk("DNUSDT", wiggle(300, g=-0.005))
    r = R.di(monday_after(START + timedelta(days=200)))
    lo, uni = R.target_weights([up, dn], r, 50, "LO")
    ls, _ = R.target_weights([up, dn], r, 50, "LS")
    assert len(uni) == 2 and "DNUSDT" not in lo and ls["DNUSDT"] < 0 < ls["UPUSDT"]
    assert all(abs(x) <= R.W_CAP + 1e-12 for x in ls.values())
    assert sum(abs(x) for x in ls.values()) <= R.GROSS_CAP + 1e-12


def test_universe_min_age_and_top_n():
    young = mk("YNGUSDT", wiggle(300), first=START + timedelta(days=150))
    r = R.di(monday_after(START + timedelta(days=200)))
    assert R.universe([young], r, 50) == []
    many = [mk(f"S{k:03d}USDT", wiggle(300), qv=1e6 + k) for k in range(60)]
    uni = R.universe(many, r, 50)
    assert len(uni) == 50 and uni[0].symbol == "S059USDT"


def test_exposure_matched_same_gross():
    up, dn = mk("UPUSDT", wiggle(300)), mk("DNUSDT", wiggle(300, g=-0.005))
    r = R.di(monday_after(START + timedelta(days=200)))
    w, uni = R.target_weights([up, dn], r, 50, "LS")
    em = R.exposure_matched(w, uni)
    assert sum(em.values()) == pytest.approx(sum(abs(x) for x in w.values()))
    assert all(x > 0 for x in em.values())


def _run(series, w, mult, n_days=60, prices_start=START):
    smap = {s.symbol: s for s in series}
    s0 = monday_after(prices_start)
    return R.simulate(smap, s0, s0 + timedelta(days=n_days), lambda t: w, mult)


def test_episode_sum_equals_equity_change_and_cost_linearity():
    s = mk("AAAUSDT", wiggle(200), funding={R.di(START) + k: 0.0003 for k in range(200)})
    for mult in (1, 2, 3):
        curve, eps, _ = _run([s], {"AAAUSDT": 0.5}, mult)
        assert sum(e["net_pnl"] for e in eps) == pytest.approx(curve[-1][1] - R.START_EQUITY, abs=1e-6)
    flat = mk("FLTUSDT", [100.0] * 200)
    c1 = _run([flat], {"FLTUSDT": 0.5}, 1)[1]
    c2 = _run([flat], {"FLTUSDT": 0.5}, 2)[1]
    assert sum(e["cost"] for e in c2) == pytest.approx(2 * sum(e["cost"] for e in c1), rel=1e-3)
    c0 = _run([flat], {"FLTUSDT": 0.5}, 0)[1]
    assert sum(e["cost"] for e in c0) == 0


def test_funding_sign_long_pays_short_receives():
    flat = mk("FLTUSDT", [100.0] * 200, funding={R.di(START) + k: 0.001 for k in range(200)})
    long_ = _run([flat], {"FLTUSDT": 0.5}, 0)[1]
    short = _run([flat], {"FLTUSDT": -0.5}, 0)[1]
    assert sum(e["funding"] for e in long_) < 0 < sum(e["funding"] for e in short)


def test_funding_not_on_fill_day():
    s0 = monday_after(START)
    f = {R.di(s0): 0.01}  # jen v den fillu ⇒ nezapočte se
    flat = mk("FLTUSDT", [100.0] * 200, funding=f)
    eps = _run([flat], {"FLTUSDT": 0.5}, 0)[1]
    assert sum(e["funding"] for e in eps) == 0


def test_short_liquidation_loses_notional():
    n = 200
    s0 = monday_after(START)
    k0 = (s0 - START).days
    highs = [100.0] * n
    highs[k0 + 3] = 250.0
    s = mk("SQZUSDT", [100.0] * n, highs=highs)
    curve, eps, st = _run([s], {"SQZUSDT": -0.1}, 0, n_days=6)
    liq = [e for e in eps if e["exit_reason"] == "liquidation"]
    assert st["liquidations"] == 1 and liq[0]["price_pnl"] == pytest.approx(-1000.0)


def test_forced_exit_on_delist():
    s0 = monday_after(START)
    k0 = (s0 - START).days
    prices = [100.0] * (k0 + 4)
    s = mk("DELUSDT", prices + [None] * 100, last=START + timedelta(days=k0 + 3))
    curve, eps, st = _run([s], {"DELUSDT": 0.2}, 1, n_days=5)
    assert st["forced_exits"] == 1 and eps[0]["exit_reason"] == "forced_exit"
    assert sum(e["net_pnl"] for e in eps) == pytest.approx(curve[-1][1] - R.START_EQUITY)


def test_neighbours():
    assert set(R.neighbours("W50_LO")) == {"W50_LS", "W100_LO"}
