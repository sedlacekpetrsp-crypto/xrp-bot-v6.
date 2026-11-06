"""Mechanika backtestu H-20261106-2 na syntetických datech (není důkaz ziskovosti)."""
from datetime import date

import pytest

from research.funding_dispersion import run as fd

H = fd.HOUR_MS
DAY = fd.DAY_MS
START = date(2021, 1, 4)  # pondělí


def make_market(days=60, price=None, rates=None, start=date(2020, 12, 1)):
    """price(a, t) a rates(a, t) volitelné; výchozí cena 100, funding 0 po 8 h."""
    t0 = fd.ms_of(start)
    market = {}
    for k, a in enumerate(fd.ASSETS):
        bars, fund = {}, {}
        for i in range(days * 24):
            t = t0 + i * H
            p = price(a, t) if price else 100.0
            hi = p if not isinstance(p, tuple) else p[1]
            p = p if not isinstance(p, tuple) else p[0]
            bars[t] = (p, max(p, hi), p, p)
            if (t // H) % 8 == 0:
                fund[t] = rates(a, t) if rates else 0.0
        market[a] = fd.prepare(bars, fund)
    return market


def ranked_rates(a, t):
    return 0.0001 * fd.ASSETS.index(a)  # BTC nejnižší … LTC nejvyšší


def test_selection_longs_lowest_shorts_highest():
    m = make_market(rates=ranked_rates)
    legs, _, dec = fd.simulate(m, START, date(2021, 1, 20), 7, 7, 1)
    d0 = dec[0]
    assert d0["longs"] == ["BTCUSDT", "ETHUSDT"]
    assert d0["shorts"] == ["DOGEUSDT", "LTCUSDT"]
    assert len(legs) == 8  # 2 koše × 4 nohy


def test_signal_uses_only_settled_rates_up_to_decision():
    D = fd.ms_of(START)
    base = make_market(rates=lambda a, t: 0.001 if t > D else 0.0)
    assert fd.funding_signal(base["BTCUSDT"], D, 7) == 0.0
    # událost přesně v D (vypořádaná) se započte, D − 7 dní ne
    m = make_market(rates=lambda a, t: 1.0 if t in (D, D - 7 * DAY) else 0.0)
    assert fd.funding_signal(m["BTCUSDT"], D, 7) == pytest.approx(1.0)


def test_prefix_invariance_of_decisions():
    m_long = make_market(days=80, rates=ranked_rates)
    m_short = make_market(days=50, rates=ranked_rates)
    _, _, d_long = fd.simulate(m_long, START, date(2021, 1, 18), 7, 7, 1)
    _, _, d_short = fd.simulate(m_short, START, date(2021, 1, 18), 7, 7, 1)
    assert d_long == d_short


def test_funding_cashflow_sign_and_boundaries():
    D = fd.ms_of(START)
    entry, exit_ = D + H, D + 7 * DAY + H
    # kladná sazba jen v době držení; LTC (short) inkasuje, BTC (long) platí; hraniční události se nepočítají
    def rates(a, t):
        if t <= D:
            return ranked_rates(a, t)
        return 0.001 if entry < t < exit_ else 0.0
    m = make_market(rates=rates)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    n_events = sum(1 for t in m["BTCUSDT"]["funding"] if entry < t < exit_)
    assert n_events == 21
    by = {lg["asset"]: lg for lg in legs}
    qty = by["BTCUSDT"]["qty"]
    assert by["BTCUSDT"]["funding"] == pytest.approx(-0.001 * qty * 100 * 21)
    assert by["LTCUSDT"]["funding"] == pytest.approx(0.001 * by["LTCUSDT"]["qty"] * 100 * 21)


def test_costs_scale_linearly():
    m = make_market(rates=ranked_rates)
    res = {}
    for mult in (1, 2, 3):
        legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, mult)
        res[mult] = sum(lg["costs"] for lg in legs)
    assert res[2] == pytest.approx(2 * res[1])
    assert res[3] == pytest.approx(3 * res[1])
    assert res[1] == pytest.approx(4 * 1000 * (fd.FEE + fd.SLIP) * 2)


def test_short_leg_liquidation_at_double_price():
    D = fd.ms_of(START)
    def price(a, t):
        if a == "LTCUSDT" and t >= D + 3 * DAY:
            return (100.0, 250.0)
        return 100.0
    m = make_market(price=price, rates=ranked_rates)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    ltc = [lg for lg in legs if lg["asset"] == "LTCUSDT"][0]
    assert ltc["liquidated"] == 1
    assert ltc["gross"] == pytest.approx(-ltc["notional"])


def test_long_short_pnl_and_no_overlap():
    D = fd.ms_of(START)
    def price(a, t):
        if t <= D + H:
            return 100.0
        return 110.0 if a in ("BTCUSDT", "ETHUSDT") else 90.0
    m = make_market(price=price, rates=ranked_rates)
    legs, curve, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    first = [lg for lg in legs if lg["entry_ts"] == D + H]
    assert len(first) == 4
    for lg in first:
        assert lg["gross"] == pytest.approx(lg["notional"] * 0.10)  # long +10 %, short z poklesu 10 %
    ends = sorted((lg["entry_ts"], lg["exit_ts"]) for lg in legs)
    assert all(e <= s2 for (_, e), (s2, _) in zip(ends[::4], ends[4::4]))
    assert curve[date(2021, 1, 4)] > fd.START_EQUITY


def test_skips_week_when_too_few_eligible():
    m = make_market(rates=ranked_rates)
    for a in fd.ASSETS[:3]:
        m[a] = fd.prepare({}, {})
    legs, curve, dec = fd.simulate(m, START, date(2021, 1, 20), 7, 7, 1)
    assert legs == [] and all(d["skipped"] for d in dec)
    assert set(curve.values()) == {fd.START_EQUITY}


def test_buy_hold_and_evaluate_shapes():
    m = make_market(rates=ranked_rates)
    bh, rets = fd.buy_hold(m, START, date(2021, 1, 20), 1)
    assert bh["net_pnl"] < 0 and len(rets) == 17
    assert set(fd.neighbors(7, 7)) == {(7, 14), (14, 7)}


# ---- regresní testy na žádost oponentury ChatGPT (DIALOG.md kolo 1) ----
def _first_basket(legs, D):
    return sorted(((lg["asset"], lg["side"], lg["entry_ts"], lg["exit_ts"], round(lg["qty"], 9),
                    round(lg["funding"], 9), round(lg["net_pnl"], 9)) for lg in legs if lg["entry_ts"] == D + H))


def test_funding_exactly_at_entry_and_exit_is_excluded():
    D = fd.ms_of(START)
    entry, exit_ = D + H, D + 7 * DAY + H
    m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
    for a in fd.ASSETS:  # nenulová sazba přesně na hranách (01:00) – nesmí se započíst
        f = dict(m[a]["funding"])
        f[entry] = f[exit_] = 0.05
        m[a] = fd.prepare(m[a]["bars"], f)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    first = [lg for lg in legs if lg["entry_ts"] == entry]
    assert len(first) == 4 and all(lg["funding"] == 0.0 for lg in first)
    assert fd.simulate_edge_events(m, legs) == 8  # 4 nohy × (vstup + výstup), vykázáno informativně


def test_funding_one_hour_inside_edges_is_included_once():
    D = fd.ms_of(START)
    entry, exit_ = D + H, D + 7 * DAY + H
    m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
    for a in fd.ASSETS:
        f = dict(m[a]["funding"])
        f[entry + H] = f[exit_ - H] = 0.001
        m[a] = fd.prepare(m[a]["bars"], f)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    for lg in [x for x in legs if x["entry_ts"] == entry]:
        assert lg["funding"] == pytest.approx(-lg["side"] * 0.001 * lg["qty"] * 100 * 2)


def test_changing_future_data_does_not_change_earlier_decisions_weights_fills():
    """Kauzalita: data po výstupu prvního koše se ZMĚNÍ (ne jen připojí) ⇒ 1. koš beze změny."""
    D = fd.ms_of(START)
    cut = D + 7 * DAY + H  # výstup 1. koše
    base = make_market(days=60, rates=ranked_rates)
    alt = make_market(days=60, price=lambda a, t: 100.0 if t <= cut else (300.0, 900.0),
                      rates=lambda a, t: ranked_rates(a, t) if t <= cut else (-1) ** fd.ASSETS.index(a) * 0.01)
    lb, _, db = fd.simulate(base, START, date(2021, 1, 25), 7, 7, 1)
    la, _, da = fd.simulate(alt, START, date(2021, 1, 25), 7, 7, 1)
    assert _first_basket(lb, D) == _first_basket(la, D)
    assert db[0] == da[0] and db[1] == da[1]  # 2. rozhodnutí (11. 1. 00:00) leží před změnou v 01:00
    assert db[2] != da[2]  # 3. rozhodnutí už vidí změněný funding ⇒ test má sílu


def test_costs_charged_on_all_four_legs_entry_and_exit():
    m = make_market(rates=lambda a, t: 0.0001 * fd.ASSETS.index(a) if t <= fd.ms_of(START) else 0.0)
    legs, curve, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    c = fd.FEE + fd.SLIP
    assert len(legs) == 4
    for lg in legs:
        assert lg["costs"] == pytest.approx(2 * 1000 * c) and lg["net_pnl"] == pytest.approx(-2 * 1000 * c)
    assert curve[date(2021, 1, 11)] == pytest.approx(fd.START_EQUITY - 8 * 1000 * c)


def test_vol_matched_benchmark_info():
    out = fd.vol_matched(strategy_rets=[0.01, -0.01] * 10, bh_rets=[0.04, -0.04] * 10)
    assert out["scale"] == pytest.approx(0.25)
    assert 0 < out["max_drawdown_pct"] < 2
