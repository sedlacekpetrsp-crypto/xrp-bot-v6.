"""Mechanika backtestu H-20261106-2 na syntetických datech (není důkaz ziskovosti)."""
from datetime import date

import pytest

from research.funding_dispersion import run as fd

H = fd.HOUR_MS
DAY = fd.DAY_MS
START = date(2021, 1, 4)  # pondělí


def valid_decision(manifest=(), missing=(), **kw):
    """Úplný záznam rozhodnutí (kolo 6, bod 5) pro syntetické testy brány."""
    return {"semantics": "B", "evidence": "test", "decided_utc": "test", "audit_id": "run-test",
            "impl_sha256": fd.impl_fingerprint(), "data_manifest_sha256": fd.manifest_fingerprint(list(manifest), list(missing)),
            "performance_hold": False, **kw}


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
    ts, t = [], D - 10 * DAY
    while t <= D + 3 * DAY:
        ts.append(t)
        t += (8 if t < D - 5 * DAY else (4 if t < D - 2 * DAY else 1)) * H
    # sémantika B: interval záznamu = délka úseku končícího touto událostí
    f = {t: (0.0001, float((t - p) // H if p is not None else 8)) for p, t in zip([None] + ts[:-1], ts)}
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
    (tmp_path / fd.SEMANTICS_FILE).write_text(_j.dumps(valid_decision()))
    fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
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
    assert a["spacing_mismatch_semantics_B_tolerant_implemented"] == 0


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
        fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
    assert e.value.code == 3 and called == []  # odmítnuto ještě před načtením dat
    import json
    ok = valid_decision()
    for bad in ({**ok, "semantics": "C"}, {"semantics": "B"}, {**ok, "semantics": "A"},  # A ≠ implementace
                {**ok, "performance_hold": True}, {k: v for k, v in ok.items() if k != "performance_hold"}):
        (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(bad))
        assert fd.semantics_gate(tmp_path)[0] is False
    (tmp_path / fd.SEMANTICS_FILE).write_text("{nejson")
    assert fd.semantics_gate(tmp_path)[0] is False
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(ok))
    assert fd.semantics_gate(tmp_path) == (True, "ok")


def test_committed_decision_keeps_performance_blocked():
    """Zapsané rozhodnutí ve větvi: sémantika B, ale výkonnost pozastavena vlastníkem ⇒ runner výpočet odmítne."""
    from pathlib import Path
    import json
    d = json.loads((Path(fd.__file__).parent / fd.SEMANTICS_FILE).read_text())
    assert d["semantics"] == "B" == fd.IMPLEMENTED_SEMANTICS and d["performance_hold"] is True
    assert fd.semantics_gate(Path(fd.__file__).parent)[0] is False


def test_gate_does_not_block_audit_only(tmp_path, monkeypatch):
    m = make_market(rates=ranked_rates)
    monkeypatch.setattr(fd, "load", lambda cache: (m, [], [], []))
    fd.main(["--outdir", str(tmp_path), "--audit-only"])
    assert (tmp_path / "data_audit.json").exists() and not (tmp_path / "results.json").exists()


def test_semantics_B_real_SOL_november_2022_pattern():
    """Skutečný sled SOLUSDT z data_audit.json (run 42256020278): 8 h → 4 h → 2 h (změna uprostřed úseku) → 8 h."""
    seq = [("2022-11-09T00", 8), ("2022-11-09T08", 8), ("2022-11-09T16", 8), ("2022-11-09T20", 4), ("2022-11-10T00", 4),
           ("2022-11-10T04", 2), ("2022-11-10T06", 2), ("2022-11-10T08", 2)]
    from datetime import datetime, timezone
    ms = lambda x: int(datetime.fromisoformat(x + ":00:00").replace(tzinfo=timezone.utc).timestamp() * 1000)
    f = {ms(t): (0.0001, float(iv)) for t, iv in seq}
    f.update({ms("2022-11-18T04") + k * 2 * H: (0.0001, 2.0) for k in range(3)})
    f.update({ms("2022-11-18T16"): (0.0001, 8.0), ms("2022-11-19T00"): (0.0001, 8.0)})
    m = fd.prepare({}, f)
    lo, hi = ms("2022-11-09T00"), ms("2022-11-10T08")
    assert fd.funding_chain_gaps(m, lo, hi) == 0
    assert fd.funding_chain_gaps(m, ms("2022-11-18T04"), ms("2022-11-19T00")) == 0
    assert fd.funding_chain_gaps(m, lo, hi) == 0 and fd.funding_chain_gaps(m, lo - 1, hi) is None
    del f[ms("2022-11-10T06")]  # skutečně chybějící událost se dál označí
    assert fd.funding_chain_gaps(fd.prepare({}, f), lo, hi) == 1


# ---- kolo 6 (oponentura kol 4–6): testy DOKAZUJÍCÍ OPRAVU ----
BH_DAY = date(2021, 1, 4)


def _flat_market(rate=0.01, drop=()):
    """Ploché ceny 100, funding `rate` v 00/08/16 UTC; drop = [(aktivum|None, ts)] odstraní událost (None = všem)."""
    m = make_market(rates=lambda a, t: rate)
    for who, ts in drop:
        for a in fd.ASSETS if who is None else (who,):
            f = {t: (r, 8.0) for t, r in m[a]["funding"].items() if t != ts}
            m[a] = fd.prepare(m[a]["bars"], f)
    return m


def test_K6_1_bh_complete_series_reference_values():
    bh, _ = fd.buy_hold(_flat_market(), BH_DAY, BH_DAY, 1)
    assert bh["funding"] == pytest.approx(-199.77, abs=1e-4) and bh["net_pnl"] == pytest.approx(-222.7568, abs=1e-4)
    assert (bh["funding_missing_events"], bh["funding_discontinuities"], bh["funding_unknown_coverage_assets"]) == (0, 0, 0)


def test_K6_1_bh_gap_middle_is_counted_per_asset_not_hidden():
    t08 = fd.ms_of(BH_DAY) + 8 * H
    bh, _ = fd.buy_hold(_flat_market(drop=[(None, t08)]), BH_DAY, BH_DAY, 1)
    assert bh["funding"] == pytest.approx(-99.885, abs=1e-4)  # účtování beze změny, chybějící sazba ≠ 0 se neodhaduje
    assert bh["funding_missing_events"] == 8 and bh["funding_discontinuities"] == 8  # 8 aktiv PR #29, ne 12
    assert all(c == {"discontinuities": 1, "missing_events": 1, "unknown_coverage": False}
               for c in bh["funding_completeness"].values())


def test_K6_1_bh_gap_prefix_suffix_and_unknown_coverage():
    t0 = fd.ms_of(BH_DAY)
    pre, _ = fd.buy_hold(_flat_market(drop=[("BTCUSDT", t0)]), BH_DAY, BH_DAY, 1)  # chybí událost, na kterou navazuje držení
    suf, _ = fd.buy_hold(_flat_market(drop=[("ETHUSDT", t0 + 16 * H)]), BH_DAY, BH_DAY, 1)  # chybí poslední před prodejem
    assert (pre["funding_missing_events"], pre["funding_discontinuities"]) == (1, 1)
    assert (suf["funding_missing_events"], suf["funding_discontinuities"]) == (1, 1)
    m = _flat_market()
    f = {t: (r, 8.0) for t, r in m["XRPUSDT"]["funding"].items() if t > t0}  # funding začíná až po nákupu
    m["XRPUSDT"] = fd.prepare(m["XRPUSDT"]["bars"], f)
    unk, _ = fd.buy_hold(m, BH_DAY, BH_DAY, 1)
    assert unk["funding_unknown_coverage_assets"] == 1


def test_K6_1_negative_rate_gap_blocks_too():
    t08 = fd.ms_of(BH_DAY) + 8 * H
    bh, _ = fd.buy_hold(_flat_market(rate=-0.01, drop=[(None, t08)]), BH_DAY, BH_DAY, 1)
    assert bh["funding"] > 0 and bh["funding_missing_events"] == 8
    flags = {k: 0 for k in fd.DATA_DEFECTS} | {"benchmark_funding_missing_events": bh["funding_missing_events"]}
    assert fd.final_verdict(True, False, {"r": True}, flags)[0].startswith("NEROZHODNUTO")


def test_K6_2_funding_window_open_both_ends_shared_by_strategy_and_benchmark():
    m = _flat_market()["BTCUSDT"]
    t0 = fd.ms_of(BH_DAY)
    assert fd.funding_window(m, t0, t0 + DAY) == [t0 + 8 * H, t0 + 16 * H]  # 00:00 vstup a 00:00 výstup se neúčtují
    # tatáž hranice v kontrole úplnosti: chybějící událost přesně ve výstupu není mezera
    f = {t: (r, 8.0) for t, r in m["funding"].items() if t != t0 + DAY}
    assert fd.funding_completeness(fd.prepare(m["bars"], f), t0, t0 + DAY)["missing_events"] == 0
    # strategie: událost v hodině vstupu / uvnitř / ve výstupu
    D = fd.ms_of(START)
    entry, exit_ = D + H, D + 7 * DAY + H
    mm = make_market(rates=lambda a, t: ranked_rates(a, t) if t <= D else 0.0)
    for a in fd.ASSETS:
        f = dict(mm[a]["funding"])
        f[entry] = f[exit_] = f[entry + 3 * H] = 0.002
        mm[a] = fd.prepare(mm[a]["bars"], f)
    legs, _, _ = fd.simulate(mm, START, date(2021, 1, 11), 7, 7, 1)
    for lg in [x for x in legs if x["entry_ts"] == entry]:
        assert lg["funding"] == pytest.approx(-lg["side"] * 0.002 * lg["qty"] * 100)  # jen událost uvnitř


def test_K6_2_completeness_discontinuities_equal_chain_gaps():
    m = _flat_market(drop=[("BTCUSDT", fd.ms_of(BH_DAY) + 8 * H)])["BTCUSDT"]
    lo, hi = fd.ms_of(BH_DAY) - 3 * DAY, fd.ms_of(BH_DAY) + 2 * DAY
    assert fd.funding_completeness(m, lo, hi)["discontinuities"] == fd.funding_chain_gaps(m, lo, hi - 1) == 1


def test_K6_3_registry_every_flag_classified_unknown_raises_informational_does_not_block():
    m = make_market(rates=ranked_rates)
    res = {p: {"x1": fd.run(m, START, date(2021, 1, 20), 1, 7, 7, "t")[0]} for p in fd.PERIODS}
    bh = {p: {"x1": fd.buy_hold(m, START, date(2021, 1, 20), 1)[0]} for p in fd.PERIODS}
    flags = fd.defect_flags(res, bh, m)
    assert set(flags) <= set(fd.DATA_DEFECTS) and set(fd.DATA_DEFECTS.values()) == {"blocking", "informational"}
    with pytest.raises(KeyError):
        fd.blocking_defects({**flags, "nove_pocitadlo": 1})
    info = {k: 0 for k in fd.DATA_DEFECTS} | {"duplicate_funding_rows_same_value": 5}
    assert fd.final_verdict(True, True, {"r": True}, info) == ("KANDIDÁT NA FORWARD PAPER", {})
    assert fd.DATA_DEFECTS["benchmark_price_fallbacks"] == "blocking"


def test_K6_3_benchmark_price_fallback_counted():
    m = _flat_market()
    b = dict(m["BTCUSDT"]["bars"])
    del b[fd.ms_of(BH_DAY) + 8 * H]  # chybí svíčka v čase fundingu, předchozí close je čerstvý
    m["BTCUSDT"] = fd.prepare(b, {t: (r, 8.0) for t, r in m["BTCUSDT"]["funding"].items()})
    bh, _ = fd.buy_hold(m, BH_DAY, BH_DAY, 1)
    assert bh["price_fallbacks"] == 1


def test_K6_4_unfilled_entry_record_without_fake_position_fee_or_cooldown():
    D = fd.ms_of(START)
    m = make_market(rates=lambda a, t: 0.0001 * ((fd.ASSETS.index(a) * 3) % 8) if t <= D else 0.0)
    _, _, d0 = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    gone = d0[0]["longs"][0]
    b = dict(m[gone]["bars"])
    del b[D + H]
    m[gone] = fd.prepare(b, m[gone]["funding"])
    legs, curve, d1 = fd.simulate(m, START, date(2021, 1, 11), 7, 7, 1)
    assert d1[0]["unfilled_entries"] == [{"asset": gone, "side": 1, "entry_utc": "2021-01-04T01:00:00+00:00",
                                         "planned_notional": 1000.0, "reason": "missing_entry_bar"}]
    c = fd.FEE + fd.SLIP
    assert len(legs) == 3 and curve[date(2021, 1, 11)] == pytest.approx(fd.START_EQUITY - 6 * 1000 * c)
    r = fd.run(m, START, date(2021, 1, 11), 1, 7, 7, "t")[0]
    assert r["unfilled_entry_legs"] == 1 and r["unfilled_entries"][0]["reason"] == "missing_entry_bar"


# ---- kolo 6, bod 5: brána výkonnosti ----
def _boom(*a, **k):
    raise AssertionError("simulace nesmí být zavolána")


def _guard(monkeypatch, market=None, manifest=()):
    calls = {"load": 0}

    def load(cache):
        calls["load"] += 1
        return market or {}, list(manifest), [], []
    monkeypatch.setattr(fd, "load", load)
    for f in ("simulate", "run", "buy_hold"):
        monkeypatch.setattr(fd, f, _boom)
    return calls


@pytest.mark.parametrize("decision", [None, "{nejson", {"semantics": "B"},
                                      valid_decision(performance_hold=True), valid_decision(audit_id=""),
                                      valid_decision(impl_sha256="0" * 64), valid_decision(semantics="A")])
def test_K6_5_invalid_decision_no_load_no_sim_no_metrics(tmp_path, monkeypatch, decision):
    import json
    if decision is not None:
        (tmp_path / fd.SEMANTICS_FILE).write_text(decision if isinstance(decision, str) else json.dumps(decision))
    calls = _guard(monkeypatch)
    with pytest.raises(SystemExit) as e:
        fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
    assert e.value.code == 3 and calls["load"] == 0
    assert not any((tmp_path / f).exists() for f in ("results.json", "trades.csv", "data_source.json"))


def test_K6_5_changed_data_loads_but_never_simulates(tmp_path, monkeypatch):
    import json
    audited = [{"url": "u1", "sha256": "a" * 64, "rows": 1}]
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(valid_decision(manifest=audited)))
    calls = _guard(monkeypatch, manifest=[{"url": "u1", "sha256": "b" * 64, "rows": 1}])
    with pytest.raises(SystemExit) as e:
        fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
    assert e.value.code == 3 and calls["load"] == 1
    assert not any((tmp_path / f).exists() for f in ("results.json", "trades.csv", "data_source.json"))


def test_K6_5_valid_gate_reaches_simulation_with_mocked_performance(tmp_path, monkeypatch):
    import json
    audited = [{"url": "u1", "sha256": "a" * 64, "rows": 1}]
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(valid_decision(manifest=audited)))
    _guard(monkeypatch, market=make_market(rates=ranked_rates), manifest=audited)

    class Reached(Exception):
        pass

    def reached(*a, **k):
        raise Reached
    monkeypatch.setattr(fd, "run", reached)
    with pytest.raises(Reached):
        fd.main(["--outdir", str(tmp_path), "--mode", "perf"])


def test_K6_5_audit_never_simulates_and_disowns_old_results(tmp_path, monkeypatch):
    import json
    (tmp_path / "results.json").write_text("{\"stary\": true}")
    _guard(monkeypatch, market=make_market(rates=ranked_rates))
    fd.main(["--outdir", str(tmp_path), "--mode", "audit"])
    man = json.loads((tmp_path / fd.AUDIT_MANIFEST_FILE).read_text())
    assert man["mode"] == "audit" and "results.json" not in man["produced_by_this_run"]
    assert man["preexisting_performance_files_not_from_this_run"] == ["results.json"]
    assert json.loads((tmp_path / "results.json").read_text()) == {"stary": True}  # nepřepsáno, nevydáváno za nové


@pytest.mark.parametrize("text,code", [("BACKTEST 2026", 4), ("", 4), ("audit malými", 4)])
def test_K6_5_unknown_mode_refused(tmp_path, monkeypatch, text, code):
    req = tmp_path / "RUN_REQUEST"
    req.write_text(text)
    calls = _guard(monkeypatch)
    with pytest.raises(SystemExit) as e:
        fd.main(["--outdir", str(tmp_path), "--request-file", str(req)])
    assert e.value.code == code and calls["load"] == 0


def test_K6_5_missing_or_conflicting_mode_refused(tmp_path, monkeypatch):
    calls = _guard(monkeypatch)
    for argv in ([], ["--audit-only", "--mode", "perf"]):
        with pytest.raises(SystemExit) as e:
            fd.main(["--outdir", str(tmp_path), *argv])
        assert e.value.code == 4
    with pytest.raises(SystemExit) as e:
        fd.main(["--outdir", str(tmp_path), "--mode", "backtest"])  # argparse choices
    assert e.value.code == 2 and calls["load"] == 0


def test_K6_5_committed_request_is_audit_and_decision_still_blocks():
    from pathlib import Path
    here = Path(fd.__file__).parent
    assert fd.mode_from_request(here / "RUN_REQUEST") == "audit"
    ok, why = fd.semantics_gate(here)
    assert ok is False and "performance_hold" in why


def test_K6_integration_verdict_blocked_by_benchmark_gap_else_candidate(tmp_path, monkeypatch):
    """Celá větev main → buy_hold → defect_flags → final_verdict → results.json na syntetických datech; výkonnostní
    kritéria a robustnost vynuceně splněné (mock), aby rozhodovala jen datová brána."""
    import json
    monkeypatch.setattr(fd, "PERIODS", {"tuning": ("2021-01-04", "2021-01-17"), "validation": ("2021-01-18", "2021-01-31"),
                                        "final_test": ("2021-02-01", "2021-02-14")})
    monkeypatch.setattr(fd, "WF_YEARS", ())
    monkeypatch.setattr(fd, "evaluate", lambda res, bh: ({"A": True}, {"B": True}))
    monkeypatch.setattr(fd, "robustness_checks", lambda dsr, nb, wf: {"mock": True})
    monkeypatch.setattr(fd, "safe_dsr", lambda r, n, v: {"dsr": None, "undefined_reason": "mock"})
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))

    def go(market):
        monkeypatch.setattr(fd, "load", lambda cache: (market, [], [], []))
        fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
        return json.loads((tmp_path / "results.json").read_text())
    clean = go(make_market(days=90, rates=ranked_rates))
    assert clean["verdict"] == "KANDIDÁT NA FORWARD PAPER" and clean["blocking_data_defects"] == {}
    bad = make_market(days=90, rates=ranked_rates)
    t = fd.ms_of(date(2021, 1, 20)) + 8 * H  # mezera fundingu BTC ve validaci (zasáhne i benchmark)
    bad["BTCUSDT"] = fd.prepare(bad["BTCUSDT"]["bars"], {k: v for k, v in bad["BTCUSDT"]["funding"].items() if k != t})
    out = go(bad)
    assert out["verdict"].startswith("NEROZHODNUTO")
    assert out["blocking_data_defects"].get("benchmark_funding_missing_events") == 1
