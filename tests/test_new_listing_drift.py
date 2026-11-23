"""Mechanika A1 NEW-LISTING DRIFT na syntetických datech (ne důkaz výkonnosti)."""
from datetime import date, timedelta

import pytest

from research.new_listing_drift import run as R

D0 = date(2023, 1, 1)


def mk(prices, start=D0, vol=1.0, highs=None, funding=()):
    bars = {}
    for i, p in enumerate(prices):
        h = highs[i] if highs else p
        bars[start + timedelta(days=i)] = (p, h, p, p, vol)
    return R.Series(bars, list(funding))


def listing(L=D0, last=None, sym="AAAUSDT"):
    return {"symbol": sym, "L": L, "last_day": last or L + timedelta(days=400)}


def test_plan_entry_exit_open():
    s = mk([1.0] * 300)
    p, why = R.plan(listing(), s, 30, 90)
    assert why is None and p["entry"] == D0 + timedelta(30) and p["exit_day"] == D0 + timedelta(90)
    assert p["exit_kind"] == "open"


def test_plan_delist_before_entry_and_forced():
    s = mk([1.0] * 50)
    assert R.plan(listing(last=D0 + timedelta(20)), s, 30, 90) == (None, "delist_before_entry")
    p, _ = R.plan(listing(last=D0 + timedelta(49)), s, 30, 90)
    assert p["exit_kind"] == "close_forced_delist" and p["exit_day"] == D0 + timedelta(49)


def test_plan_entry_shift_and_skip():
    bars = {D0 + timedelta(i): (1, 1, 1, 1, 1.0) for i in range(300)}
    for i in (30, 31):
        bars[D0 + timedelta(i)] = (1, 1, 1, 1, 0.0)  # nulový objem = neobchodní den
    s = R.Series(bars, [])
    p, _ = R.plan(listing(), s, 30, 90)
    assert p["entry"] == D0 + timedelta(32)
    for i in (32, 33):
        bars[D0 + timedelta(i)] = (1, 1, 1, 1, 0.0)
    assert R.plan(listing(), R.Series(bars, []), 30, 90) == (None, "no_entry_bar")


def test_entry_prefix_invariance():
    a = mk([1.0] * 300)
    prices = [1.0] * 31 + [5.0] * 269  # budoucnost po E se liší
    b = mk(prices)
    pa, _ = R.plan(listing(), a, 30, 90)
    pb, _ = R.plan(listing(), b, 30, 90)
    assert pa["entry"] == pb["entry"]


def test_short_pnl_costs_linear():
    s = mk([100.0] * 30 + [100.0] + [100.0] * 59 + [50.0] * 10)
    r = {m: R.simulate_short(s, D0 + timedelta(30), D0 + timedelta(90), "open", m) for m in (0, 1, 2, 3)}
    assert r[0]["net_pnl"] == pytest.approx(50.0)  # 100 USDT notional, cena půlka
    d1 = r[0]["net_pnl"] - r[1]["net_pnl"]
    assert r[0]["net_pnl"] - r[2]["net_pnl"] == pytest.approx(2 * d1, rel=1e-2)  # qty = notional/fill ⇒ téměř lineární
    assert r[0]["gross_ret"] == pytest.approx(0.5)


def test_liquidation():
    highs = [1.0] * 40 + [2.5] + [1.0] * 59
    s = mk([1.0] * 100, highs=highs)
    r = R.simulate_short(s, D0 + timedelta(30), D0 + timedelta(90), "open", 1)
    assert r["exit_kind"] == "liquidation" and r["exit_day"] == D0 + timedelta(40)
    assert r["net_pnl"] == pytest.approx(-100 - 100 * R.FEE)


def test_funding_edges_excluded_and_sign():
    e, x = D0 + timedelta(30), D0 + timedelta(90)
    f = [(R.day_ms(e), 0.01), (R.day_ms(e) + 8 * 3600_000, 0.001), (R.day_ms(x), 0.01)]
    s = mk([100.0] * 100, funding=f)
    r = R.simulate_short(s, e, x, "open", 0)
    assert r["funding"] == pytest.approx(0.001 * 100)  # short dostává kladnou sazbu; hrany vynechány


def test_capacity():
    data, uni = {}, []
    for i in range(R.MAX_OPEN + 5):
        sym = f"S{i:03d}USDT"
        data[sym] = mk([1.0] * 300)
        uni.append(listing(sym=sym))
    plans, reasons = R.schedule(uni, data, 30, 90, D0, D0 + timedelta(10))
    assert len(plans) == R.MAX_OPEN and reasons["skipped_capacity"] == 5


def test_equity_end_equals_sum_and_placebo_schedule():
    data = {"AUSDT": mk([1.0] * 40 + [0.8] * 260), "BUSDT": mk([2.0] * 300)}
    uni = [listing(sym="AUSDT"), listing(L=D0 + timedelta(5), sym="BUSDT")]
    btc = mk([100.0] * 400, start=D0 - timedelta(30))
    plans, _ = R.schedule(uni, data, 30, 90, D0, D0 + timedelta(30))
    tr, cv = R.run_block(plans, data, 1)
    assert cv[-1][1] == pytest.approx(R.START_EQUITY + sum(t["net_pnl"] for t in tr))
    ptr, _ = R.run_block(plans, data, 1, placebo=btc)
    assert [(t["entry_day"], t["exit_day"]) for t in ptr] == [(t["entry_day"], t["exit_day"]) for t in tr]
    assert cv[0][1] == R.START_EQUITY


def test_equity_marks_open_position():
    data = {"AUSDT": mk([1.0] * 50 + [0.5] * 250)}
    plans, _ = R.schedule([listing(sym="AUSDT")], data, 30, 90, D0, D0)
    tr, cv = R.run_block(plans, data, 0)
    mid = dict(cv)[D0 + timedelta(60)]
    assert mid == pytest.approx(R.START_EQUITY + 50.0)


def test_universe_excludes_archive_start():
    uni = R.load_universe()
    assert uni and min(u["L"] for u in uni) >= R.UNIVERSE_FROM
