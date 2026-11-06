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


# ---- kolo 2 oponentury ChatGPT: R1–R4 a body B, D, E ----
def test_R1_repro_sparse_data_is_not_eligible():
    D = fd.ms_of(START)
    m = {"BTCUSDT": fd.prepare({D - 20 * DAY: (1, 1, 1, 1), D + H: (1, 1, 1, 1)}, {D - 20 * DAY: 0.0})}
    ok, why = fd.eligibility(m, "BTCUSDT", D, 7, D + H)
    assert ok is False and why == "price_gap_in_window"


def test_R1_missing_funding_event_inside_window_makes_ineligible_not_zero():
    D = fd.ms_of(START)
    m = make_market(rates=ranked_rates)
    a = "ETHUSDT"
    f = dict(m[a]["funding"])
    del f[D - 2 * DAY]  # vnitřní mezera
    m[a] = fd.prepare(m[a]["bars"], f)
    assert fd.eligibility(m, a, D, 7, D + H) == (False, "funding_gap_in_window")
    _, _, dec = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    assert a not in dec[0]["signal"] and dec[0]["ineligible_reasons"] == {a: "funding_gap_in_window"}


def test_R1_interval_change_8h_4h_1h_is_continuous():
    D = fd.ms_of(START)
    bars = {D - 10 * DAY + i * H: (100.0, 100.0, 100.0, 100.0) for i in range(12 * 24)}
    f, t = {}, D - 10 * DAY
    while t <= D + 3 * DAY:
        iv = 8 if t < D - 5 * DAY else (4 if t < D - 2 * DAY else 1)
        f[t] = (0.0001, float(iv))
        t += iv * H
    m = {"BTCUSDT": fd.prepare(bars, f)}
    assert fd.eligibility(m, "BTCUSDT", D, 7, D + H) == (True, "ok")
    # počet událostí v okně odpovídá intervalům: 8h do D−5 d, 4h do D−2 d, 1h do D
    assert fd.funding_signal(m["BTCUSDT"], D, 7) == pytest.approx(0.0001 * (6 + 18 + 48))


def test_R1_duplicate_after_normalization():
    audit = {"duplicates_same_value": 0}
    store = {}
    fd.add_funding(store, [(0, 0.001, 8.0, 5), (0, 0.001, 8.0, 12)], "BTCUSDT", audit)
    assert audit["duplicates_same_value"] == 1 and len(store) == 1
    with pytest.raises(ValueError):
        fd.add_funding(store, [(0, 0.002, 8.0, 7)], "BTCUSDT", audit)
    with pytest.raises(ValueError):
        fd.normalize_funding_ts(3 * H + 1500)


def test_R2_benchmark_accounts_funding_sign():
    res = {}
    for r in (0.0, 0.01, -0.01):
        mk = make_market(rates=lambda a, t, r=r: r)
        res[r] = fd.buy_hold(mk, START, date(2021, 1, 11), 1)[0]
    assert res[0.0]["net_pnl"] == pytest.approx(-22.9868, abs=1e-4)
    assert res[0.01]["net_pnl"] < res[0.0]["net_pnl"] < res[-0.01]["net_pnl"]
    # 8 dní × 3 události, každá 1 % z 9 988,5 notional (po vstupních nákladech); poslední den 00:00 je uvnitř
    n_events = sum(1 for t in mk["BTCUSDT"]["fts"] if fd.ms_of(START) < t <= fd.ms_of(date(2021, 1, 11)) + 23 * H)
    assert res[0.01]["funding"] == pytest.approx(-0.01 * fd.START_EQUITY * (1 - (fd.FEE + fd.SLIP)) * n_events)


def test_R3_gap_through_liquidation_at_exit_open():
    D = fd.ms_of(START)
    exit_ = D + 7 * DAY + H
    def price(a, t):
        return 300.0 if a == "LTCUSDT" and t >= exit_ else 100.0
    m = make_market(price=price, rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    ltc = [lg for lg in legs if lg["asset"] == "LTCUSDT"][0]
    assert ltc["liquidated"] == 1 and ltc["gross"] == pytest.approx(-1000.0) and ltc["exit_ts"] == exit_


def test_R3_high_of_exit_hour_is_not_used():
    D = fd.ms_of(START)
    exit_ = D + 7 * DAY + H
    def price(a, t):
        return (100.0, 500.0) if a == "LTCUSDT" and t == exit_ else 100.0  # open 100, high 500 až po výstupu
    m = make_market(price=price, rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    ltc = [lg for lg in legs if lg["asset"] == "LTCUSDT"][0]
    assert ltc["liquidated"] == 0 and ltc["gross"] == pytest.approx(0.0)


def test_R4_no_trades_still_writes_results_with_null_dsr(tmp_path, monkeypatch):
    t0, t1 = fd.ms_of(date(2020, 9, 1)), fd.ms_of(date(2026, 11, 1))
    bars = {t: (100.0, 100.0, 100.0, 100.0) for t in range(t0, t1, H)}
    market = {a: fd.prepare(bars, {}) for a in fd.ASSETS}  # bez fundingu ⇒ nic není způsobilé
    for a in fd.ASSETS:
        market[a]["first_funding"] = None
    monkeypatch.setattr(fd, "load", lambda cache: (market, [], [], []))
    import json as _j
    (tmp_path / fd.SEMANTICS_FILE).write_text(_j.dumps({"semantics": "A", "evidence": "test", "decided_utc": "test"}))
    fd.main(["--outdir", str(tmp_path)])
    import json
    r = json.loads((tmp_path / "results.json").read_text())
    assert r["dsr_validation_x1"]["dsr"] is None and r["dsr_validation_x1"]["undefined_reason"]
    assert r["robustness"]["dsr_ge_0_95"] is False and r["verdict"] == "ZAMÍTNUTO"
    assert r["strategy"]["W7_H7"]["validation"]["x1"]["trades"] == 0
    assert set(r["dsr_sensitivity_scenarios"]) == {f"N{n}_V{v}" for n in (159, 318, 636) for v in (0.5, 1.0, 2.0)}


def test_R4_constant_returns_dsr_undefined():
    out = fd.safe_dsr([0.0] * 731, 159, 0.5)
    assert out["dsr"] is None and "rozptyl" in out["undefined_reason"]


def test_B_basket_metrics_aggregate_four_legs():
    m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= fd.ms_of(START) else 0.0)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    b = fd.basket_metrics(legs)
    assert b["baskets"] == 1 and b["net_pnl"] == pytest.approx(sum(lg["net_pnl"] for lg in legs))


def test_D_decision_after_publication_time():
    D = fd.ms_of(START)
    m = make_market(rates=ranked_rates)
    f = {t: (r, 8.0, t + 31 if t == D else t) for t, r in m["BTCUSDT"]["funding"].items()}  # calc_time D + 31 ms
    mk = fd.prepare(m["BTCUSDT"]["bars"], f)
    assert mk["fraw"][D] == D + 31 <= fd.decision_time(D)
    assert fd.funding_signal(mk, D, 7) == pytest.approx(0.0)  # BTC sazba 0 v ranked_rates


def test_E_edge_funding_impact_is_quantified():
    D = fd.ms_of(START)
    entry = D + H
    m = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
    for a in fd.ASSETS:
        f = dict(m[a]["funding"])
        f[entry] = 0.01
        m[a] = fd.prepare(m[a]["bars"], f)
    legs, _, _ = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    n, impact = fd.simulate_edge_events(m, legs, True)
    assert n == 4 and impact == pytest.approx(4 * 0.01 * 1000)


# ---- kolo 3 oponentury ChatGPT ----
def test_K3_1_missing_future_entry_bar_does_not_change_selection():
    D = fd.ms_of(START)
    rates = lambda a, t: 0.0001 * ((fd.ASSETS.index(a) * 3) % 8)
    m = make_market(rates=rates)
    _, _, d0 = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    gone = d0[0]["longs"][0]
    b = dict(m[gone]["bars"])
    del b[D + H]
    m[gone] = fd.prepare(b, m[gone]["funding"])
    legs, _, d1 = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    assert d1[0]["signal"] == d0[0]["signal"]
    assert (d1[0]["longs"], d1[0]["shorts"]) == (d0[0]["longs"], d0[0]["shorts"])
    assert d1[0]["decision_utc"] == "2021-01-04T00:00:01+00:00"
    assert d1[0]["unfilled_legs"] == [gone] and gone not in {lg["asset"] for lg in legs}
    assert len(legs) == 3  # žádné přerankování, slot zůstal v hotovosti


def test_K3_eligibility_uses_only_bars_closed_by_decision():
    D = fd.ms_of(START)
    m = make_market(rates=ranked_rates)
    b = dict(m["BTCUSDT"]["bars"])
    del b[D]  # svíčka 00:00–01:00 se uzavře až po rozhodnutí ⇒ nesmí ovlivnit způsobilost
    m["BTCUSDT"] = fd.prepare(b, m["BTCUSDT"]["funding"])
    assert fd.eligibility(m, "BTCUSDT", D, 7) == (True, "ok")
    del b[D - H]  # svíčka 23:00–24:00 uzavřená v D ⇒ mezera
    m["BTCUSDT"] = fd.prepare(b, m["BTCUSDT"]["funding"])
    assert fd.eligibility(m, "BTCUSDT", D, 7) == (False, "price_gap_in_window")


def test_K3_data_audit_reports_interval_transitions_for_both_semantics():
    D = fd.ms_of(START)
    bars = {D - 10 * DAY + i * H: (100.0,) * 4 for i in range(12 * 24)}
    f, t = {}, D - 10 * DAY
    while t <= D:
        iv = 8 if t < D - 5 * DAY else 4
        f[t] = (0.0001, float(iv))
        t += iv * H
    m = {a: fd.prepare(bars, f) for a in fd.ASSETS}
    a = fd.data_audit(m)["BTCUSDT"]
    assert len(a["interval_transitions"]) == 1
    tr = a["interval_transitions"][0]
    assert (tr["from_h"], tr["to_h"], tr["spacing_h"]) == (8.0, 4.0, 8.0)
    assert a["spacing_mismatch_semantics_A"] == 0 and a["spacing_mismatch_semantics_B"] == 1


def test_K3_audit_only_mode_writes_audit_without_performance(tmp_path, monkeypatch):
    m = make_market(rates=ranked_rates)
    monkeypatch.setattr(fd, "load", lambda cache: (m, [], [], []))
    fd.main(["--outdir", str(tmp_path), "--audit-only"])
    assert (tmp_path / "data_audit.json").exists()
    assert not (tmp_path / "results.json").exists() and not (tmp_path / "trades.csv").exists()


# ---- dodatek 4: zámek výkonnosti bez rozhodnutí o sémantice ----
def test_gate_refuses_performance_without_semantics_decision(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(fd, "load", lambda cache: called.append(1) or ({}, [], [], []))
    with pytest.raises(SystemExit) as e:
        fd.main(["--outdir", str(tmp_path)])
    assert e.value.code == 3 and called == []  # odmítnuto ještě před načtením dat
    import json
    for bad in ({"semantics": "C", "evidence": "x", "decided_utc": "x"}, {"semantics": "A"},
                {"semantics": "B", "evidence": "x", "decided_utc": "x"}):
        (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(bad))
        assert fd.semantics_gate(tmp_path)[0] is False
    (tmp_path / fd.SEMANTICS_FILE).write_text("{nejson")
    assert fd.semantics_gate(tmp_path)[0] is False
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps({"semantics": "A", "evidence": "run 1", "decided_utc": "t"}))
    assert fd.semantics_gate(tmp_path) == (True, "ok")


def test_gate_does_not_block_audit_only(tmp_path, monkeypatch):
    m = make_market(rates=ranked_rates)
    monkeypatch.setattr(fd, "load", lambda cache: (m, [], [], []))
    fd.main(["--outdir", str(tmp_path), "--audit-only"])
    assert (tmp_path / "data_audit.json").exists() and not (tmp_path / "results.json").exists()
