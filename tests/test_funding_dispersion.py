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
    assert (fd.latest_audit_dir(tmp_path) / "data_audit.json").exists()
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
    assert (fd.latest_audit_dir(tmp_path) / "data_audit.json").exists() and not (tmp_path / "results.json").exists()


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
    assert fd.final_verdict({"A1_sharpe_dd": True}, {"B1_val_x2_profit_pf": False}, {"r": True}, flags)[0].startswith("NEROZHODNUTO")


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
    assert fd.final_verdict({"A1_sharpe_dd": True}, {"B1_val_x2_profit_pf": True}, {"r": True}, info)[:2] == \
        ("KANDIDÁT NA FORWARD PAPER", {})
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
    man = json.loads((fd.latest_audit_dir(tmp_path) / fd.AUDIT_MANIFEST_FILE).read_text())
    assert man["mode"] == "audit" and "results.json" not in man["produced_by_this_run"]
    assert man["outdir_performance_files_not_from_this_run"] == ["results.json"]
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


# ---- kolo 8: rozhodovací logika, otisk implementace, hranice fundingu, atomické audity ----
CRIT_A = ("A1_sharpe_dd", "A2_trades_ge_30", "A3_x2_pf_profit", "A4_wo_top3", "A5_final_x2")
CRIT_B = ("B1_val_x2_profit_pf", "B2_dd_le_0_6_bh", "B3_final_x2_profit", "B4_val_wo_top3", "B5_trades_ge_20",
          "B6_tuning_x1_profit")
ROBUST_OK = {"dsr_ge_0_95": True, "neighbors_val_x2_profit": True, "walk_forward_ge_3_of_4": True}
NO_FLAGS = {k: 0 for k in fd.DATA_DEFECTS}
BAD_VAL = {"validation": {"benchmark_funding_missing_events": 1}}


def tracks(fail=()):
    return ({c: c not in fail for c in CRIT_A}, {c: c not in fail for c in CRIT_B})


def test_K8_1_dependency_map_matches_evaluate_by_perturbation():
    """Závislost kritérií na benchmarku se neodvozuje z dokumentace, ale změnou benchmarku po obdobích."""
    base = {"sharpe": 1.0, "max_drawdown_pct": 10.0, "trades": 40, "profit_factor": 1.5, "net_pnl": 100.0,
            "net_without_top3": 50.0}
    res = {p: {f"x{m}": dict(base) for m in (1, 2, 3)} for p in fd.PERIODS}
    bh0 = {"sharpe": 0.5, "max_drawdown_pct": 20.0}
    found = {c: set() for c in CRIT_A + CRIT_B}
    for p in fd.PERIODS:
        for alt in ({"sharpe": 5.0, "max_drawdown_pct": 1.0}, {"sharpe": -5.0, "max_drawdown_pct": 99.0}):
            bh = {q: {f"x{m}": dict(bh0) for m in (1, 2, 3)} for q in fd.PERIODS}
            ref = {**fd.evaluate(res, bh)[0], **fd.evaluate(res, bh)[1]}
            bh[p] = {f"x{m}": dict(alt) for m in (1, 2, 3)}
            new = {**fd.evaluate(res, bh)[0], **fd.evaluate(res, bh)[1]}
            found.update({c: found[c] | {p} for c in ref if ref[c] != new[c]})
    assert {c: tuple(sorted(v)) for c, v in found.items()} == {c: tuple(sorted(v)) for c, v in fd.BENCHMARK_DEPENDENCY.items()}


def test_K8_1_clean_data_rejection_stays_rejected():
    a, b = tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh"))
    assert fd.final_verdict(a, b, ROBUST_OK, NO_FLAGS, {})[0] == "ZAMÍTNUTO"


def test_K8_1_rejection_only_by_criteria_with_bad_benchmark_is_undecided():
    a, b = tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh"))
    v, _, d = fd.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)
    assert v.startswith("NEROZHODNUTO") and (d["track_a"], d["track_b"]) == ("unknown", "unknown")


def test_K8_1_independent_rejection_kept_even_with_bad_benchmark():
    a, b = tracks(fail=("A1_sharpe_dd", "A2_trades_ge_30", "B2_dd_le_0_6_bh", "B5_trades_ge_20"))
    v, _, d = fd.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)
    assert v == "ZAMÍTNUTO" and d["track_a_reasons"] == ["A2_trades_ge_30"] and d["track_b_reasons"] == ["B5_trades_ge_20"]
    # A5 používá final_test, vada jen ve validaci ⇒ A5 je spolehlivé zamítnutí
    a, b = tracks(fail=("A5_final_x2", "B3_final_x2_profit"))
    assert fd.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)[0] == "ZAMÍTNUTO"


def test_K8_1_combinations_and_one_unknown_track():
    # stopa A neznámá (jen A1), stopa B spolehlivě zamítnutá (B3) ⇒ zamítnutí nelze prokázat pro A ⇒ NEROZHODNUTO
    a, b = tracks(fail=("A1_sharpe_dd", "B3_final_x2_profit"))
    assert fd.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)[0].startswith("NEROZHODNUTO")
    # A1 + A5 při vadě jen ve validaci: A5 spolehlivé ⇒ A zamítnuta; B jen B2 ⇒ neznámá ⇒ NEROZHODNUTO
    a, b = tracks(fail=("A1_sharpe_dd", "A5_final_x2", "B2_dd_le_0_6_bh"))
    v, _, d = fd.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)
    assert (d["track_a"], d["track_b"]) == ("fail", "unknown") and v.startswith("NEROZHODNUTO")
    # stopa prošla, benchmark vadný ⇒ NEROZHODNUTO (nikdy kandidát)
    a, b = tracks(fail=("B2_dd_le_0_6_bh",))
    flags = NO_FLAGS | {"benchmark_funding_missing_events": 1}
    assert fd.final_verdict(a, b, ROBUST_OK, flags, BAD_VAL)[0].startswith("NEROZHODNUTO")


def test_K8_1_robustness_failure_is_benchmark_independent_and_unmapped_criterion_is_conservative():
    a, b = tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh"))
    assert fd.final_verdict(a, b, {**ROBUST_OK, "dsr_ge_0_95": False}, NO_FLAGS, BAD_VAL)[0] == "ZAMÍTNUTO"
    assert fd.final_verdict({"X_new": False}, {"Y_new": False}, ROBUST_OK, NO_FLAGS, BAD_VAL)[0].startswith("NEROZHODNUTO")
    assert fd.final_verdict({"X_new": False}, {"Y_new": False}, ROBUST_OK, NO_FLAGS, {})[0] == "ZAMÍTNUTO"


def test_K8_1_benchmark_defect_periods_separate_strategy_from_benchmark():
    m = _flat_market(drop=[(None, fd.ms_of(BH_DAY) + 8 * H)])
    bh_bad = fd.buy_hold(m, BH_DAY, BH_DAY, 1)[0]
    bh_ok = fd.buy_hold(_flat_market(), BH_DAY, BH_DAY, 1)[0]
    bh = {"tuning": {"x1": bh_ok}, "validation": {"x1": bh_bad}, "final_test": {"x1": bh_ok}}
    assert fd.benchmark_defect_periods(bh) == {"validation": {"benchmark_funding_missing_events": 8,
                                                              "benchmark_funding_discontinuities": 8}}
    assert all(k.startswith("benchmark_") for k in fd.BENCHMARK_DEFECT_KEYS)


def _src():
    from pathlib import Path
    root = Path(fd.__file__).resolve().parents[2]
    return {r: (root / r).read_text() for r in fd.FINGERPRINT_SOURCES}


def test_K8_2_fingerprint_ignores_comments_docstrings_but_not_code_or_constants():
    src = _src()
    run_py, dsr_py = fd.FINGERPRINT_SOURCES
    base = fd.code_fingerprint(src)
    assert base == fd.impl_fingerprint()
    assert fd.code_fingerprint({**src, run_py: src[run_py].replace("# dny bez otevřeného koše", "# jiný komentář")}) == base
    assert fd.code_fingerprint({**src, run_py: src[run_py].replace('"""Počet chybějících hodinových svíček v [lo, hi]."""',
                                                                   '"""Jiný docstring."""')}) == base
    for old, new in (("FEE, SLIP = 0.00095, 0.0002", "FEE, SLIP = 0.00095, 0.0003"),        # náklady
                     ("LEG_FRACTION = 0.10", "LEG_FRACTION = 0.11"),                        # notional
                     ("    c = (FEE + SLIP) * mult\n    end_ms", "    c = (FEE + SLIP) * mult * 0\n    end_ms"),  # simulate
                     ("return fts[bisect.bisect_right(fts, entry)", "return fts[bisect.bisect_left(fts, entry)"),  # hranice
                     ('"benchmark_price_fallbacks": "blocking"', '"benchmark_price_fallbacks": "informational"'),
                     ("if blocking:\n", "if False:\n")):
        assert old in src[run_py], old
        assert fd.code_fingerprint({**src, run_py: src[run_py].replace(old, new, 1)}) != base, old
    assert fd.code_fingerprint({**src, dsr_py: src[dsr_py] + "\nX_NEW = 1\n"}) != base


def test_K8_2_changed_code_invalidates_previous_decision(monkeypatch, tmp_path):
    import json
    src = _src()
    run_py = fd.FINGERPRINT_SOURCES[0]
    old_fp = fd.code_fingerprint({**src, run_py: src[run_py].replace("LEG_FRACTION = 0.10", "LEG_FRACTION = 0.12")})
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(valid_decision(impl_sha256=old_fp)))
    ok, why = fd.semantics_gate(tmp_path)
    assert ok is False and "impl_sha256" in why


def test_K8_3_entry_exit_exactly_at_funding_and_empty_holding():
    m = _flat_market()["BTCUSDT"]
    t0 = fd.ms_of(BH_DAY)
    assert fd.funding_window(m, t0 + 8 * H, t0 + 16 * H) == []  # vstup i výstup přesně v události
    assert fd.funding_window(m, t0 + 8 * H, t0 + 8 * H) == []    # entry = exit
    stale = fd.prepare(m["bars"], {t: (r, 8.0) for t, r in m["funding"].items() if t < t0 - 2 * DAY})
    assert fd.funding_completeness(stale, t0, t0) == {"discontinuities": 0, "missing_events": 0, "unknown_coverage": False}
    assert fd.funding_completeness(stale, t0, t0 + H)["missing_events"] > 0  # neprázdné držení se starou řadou = mezera


def test_K8_3_interval_change_is_not_a_missing_event_but_real_gap_is():
    from datetime import datetime, timezone
    ms = lambda x: int(datetime.fromisoformat(x + ":00:00").replace(tzinfo=timezone.utc).timestamp() * 1000)
    seq = [("2022-11-09T00", 8), ("2022-11-09T08", 8), ("2022-11-09T16", 8), ("2022-11-09T20", 4), ("2022-11-10T00", 4),
           ("2022-11-10T04", 2), ("2022-11-10T06", 2), ("2022-11-10T08", 2), ("2022-11-10T10", 2)]
    f = {ms(t): (0.0001, float(iv)) for t, iv in seq}
    lo, hi = ms("2022-11-09T00"), ms("2022-11-10T10") + 1
    assert fd.funding_completeness(fd.prepare({}, f), lo, hi) == {"discontinuities": 0, "missing_events": 0,
                                                                  "unknown_coverage": False}
    del f[ms("2022-11-10T06")]
    assert fd.funding_completeness(fd.prepare({}, f), lo, hi)["missing_events"] == 1


def test_K8_3_assets_with_different_intervals_and_utc_day_boundary():
    m = make_market(days=60, rates=lambda a, t: 0.01)
    t0 = fd.ms_of(date(2020, 12, 1))
    f4 = {t0 + k * 4 * H: (0.01, 4.0) for k in range(60 * 6)}  # SOL každé 4 h
    m["SOLUSDT"] = fd.prepare(m["SOLUSDT"]["bars"], f4)
    d1, d2 = date(2021, 1, 4), date(2021, 1, 5)
    bh, _ = fd.buy_hold(m, d1, d2, 1)
    assert bh["funding_missing_events"] == 0 and bh["funding_discontinuities"] == 0
    q = fd.START_EQUITY / 8 * (1 - (fd.FEE + fd.SLIP)) / 100
    n_events = 7 * (2 + 3) + (5 + 6)  # 8h aktiva: 1. den 08/16, 2. den 00/08/16; SOL 4h: 5 + 6; 00:00 po 2. dni = prodej
    assert bh["funding"] == pytest.approx(-0.01 * q * 100 * n_events)


def test_K8_3_utc_day_boundary_event_belongs_to_new_day_in_benchmark_curve():
    m = _flat_market()
    d1, d2 = date(2021, 1, 4), date(2021, 1, 5)
    _, rets = fd.buy_hold(m, d1, d2, 1)
    bh1, _ = fd.buy_hold(m, d1, d1, 1)
    q = fd.START_EQUITY / 8 * (1 - (fd.FEE + fd.SLIP)) / 100
    # den 1 nese 08/16 (2 události), událost 5. 1. 00:00 patří dni 2 spolu s 08/16
    eq1 = fd.START_EQUITY * (1 + rets[0])
    assert eq1 == pytest.approx(fd.START_EQUITY * (1 - (fd.FEE + fd.SLIP)) - 8 * 2 * 0.01 * q * 100)
    assert bh1["funding"] == pytest.approx(-8 * 2 * 0.01 * q * 100)


def test_K8_3_duplicate_funding_conflict_raises_same_value_counted():
    audit = {"duplicates_same_value": 0}
    store = {}
    fd.add_funding(store, [(1, 0.01, 8.0, 1), (1, 0.01, 8.0, 2)], "BTCUSDT", audit)
    assert audit["duplicates_same_value"] == 1
    with pytest.raises(ValueError):
        fd.add_funding(store, [(1, 0.02, 8.0, 3)], "BTCUSDT", audit)


def _zip_csv(rows):
    import io as _io, zipfile as _zf
    buf = _io.BytesIO()
    with _zf.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "\n".join(",".join(map(str, r)) for r in rows))
    return buf.getvalue()


def test_K8_3_missing_archive_after_first_month_is_fatal(tmp_path, monkeypatch):
    import urllib.error
    monkeypatch.setattr(fd, "ASSETS", ("BTCUSDT",))
    monkeypatch.setattr(fd, "FIRST_MONTH", (2021, 1))
    monkeypatch.setattr(fd, "LAST_MONTH", (2021, 3))
    t = fd.ms_of(date(2021, 1, 1))

    def fetcher(url):
        if "2021-02" in url and "fundingRate" in url:
            raise urllib.error.HTTPError(url, 404, "nf", None, None)
        return _zip_csv([(t, 8, 0.0001)]) if "fundingRate" in url else _zip_csv([(t, 1, 1, 1, 1)])
    _, manifest, missing, fatal = fd.load(tmp_path, fetcher)
    assert fatal == [{"asset": "BTCUSDT", "kind": "fr", "month": "2021-02"}] and len(missing) == 1


def test_K8_4_unfilled_planned_notional_uses_equity_at_decision_and_is_not_duplicated():
    D = fd.ms_of(START)
    rates = lambda a, t: 0.0001 * ((fd.ASSETS.index(a) * 3) % 8)
    m = make_market(days=60, rates=rates)
    _, _, d0 = fd.simulate(m, START, date(2021, 1, 18), 7, 7, 1)
    gone = d0[1]["longs"][0]  # chybí vstup až ve 2. koši (equity po 1. koši ≠ 10 000)
    b = dict(m[gone]["bars"])
    del b[D + 7 * DAY + H]
    m[gone] = fd.prepare(b, m[gone]["funding"])
    legs, curve, dec = fd.simulate(m, START, date(2021, 1, 18), 7, 7, 1)
    eq_at_2nd = fd.START_EQUITY + sum(lg["net_pnl"] for lg in legs if lg["basket"] == 1)  # realizovaná equity v 2. rozhodnutí
    rec = dec[1]["unfilled_entries"]
    assert len(rec) == 1 and rec[0]["planned_notional"] == pytest.approx(0.1 * eq_at_2nd, abs=1e-6) and eq_at_2nd != 10_000
    r1 = fd.run(m, START, date(2021, 1, 18), 1, 7, 7, "t")[0]
    r2 = fd.run(m, START, date(2021, 1, 18), 1, 7, 7, "t")[0]
    assert r1["unfilled_entries"] == r2["unfilled_entries"] and r1["unfilled_entry_legs"] == 1  # opakování bez duplicity


def test_K8_5_concurrent_run_refused_before_load(tmp_path, monkeypatch):
    calls = _guard(monkeypatch, market=make_market(rates=ranked_rates))
    with fd.RunLock(tmp_path):
        with pytest.raises(SystemExit) as e:
            fd.main(["--outdir", str(tmp_path), "--mode", "audit"])
    assert e.value.code == 5 and calls["load"] == 0
    import json
    rec = [json.loads(x) for x in (tmp_path / fd.CONFLICT_LOG).read_text().splitlines()]
    assert len(rec) == 1 and rec[0]["event"] == "lock_conflict"  # auditní záznam konfliktu
    fd.main(["--outdir", str(tmp_path), "--mode", "audit"])  # po uvolnění projde
    assert calls["load"] == 1


def test_K8_5_atomic_write_keeps_old_content_on_failure(tmp_path, monkeypatch):
    target = tmp_path / "data_audit.json"
    target.write_text("STARÝ")

    def boom(a, b):
        raise OSError("disk")
    monkeypatch.setattr(fd.os, "replace", boom)
    with pytest.raises(OSError):
        fd.atomic_write(target, "NOVÝ")
    assert target.read_text() == "STARÝ" and [p.name for p in tmp_path.iterdir()] == ["data_audit.json"]


def test_K8_5_audit_bundle_hashes_detect_mixed_runs(tmp_path, monkeypatch):
    import json
    _guard(monkeypatch, market=make_market(rates=ranked_rates))
    fd.main(["--outdir", str(tmp_path), "--mode", "audit"])
    d = fd.latest_audit_dir(tmp_path)
    man = json.loads((d / fd.AUDIT_MANIFEST_FILE).read_text())
    src = json.loads((d / "data_source.json").read_text())
    assert man["run_id"] == src["run_id"] and set(man["files_sha256"]) == {"data_source.json", "data_audit.json"}
    assert fd.verify_audit_bundle(d) == (True, [])
    (d / "data_audit.json").write_text("{}")  # soubor z jiného běhu
    assert fd.verify_audit_bundle(d) == (False, ["data_audit.json"])
    fd.main(["--outdir", str(tmp_path), "--mode", "audit"])  # druhý audit nepřepíše první
    assert len(list((tmp_path / fd.AUDITS_DIR).iterdir())) == 2 and (d / "data_audit.json").read_text() == "{}"


def test_K8_5_audit_does_not_touch_performance_files(tmp_path, monkeypatch):
    (tmp_path / "results.json").write_text("PERF")
    (tmp_path / "trades.csv").write_text("PERF")
    _guard(monkeypatch, market=make_market(rates=ranked_rates))
    fd.main(["--outdir", str(tmp_path), "--mode", "audit"])
    assert (tmp_path / "results.json").read_text() == "PERF" and (tmp_path / "trades.csv").read_text() == "PERF"


def test_K8_integration_main_rejected_vs_undecided_by_benchmark(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(fd, "PERIODS", {"tuning": ("2021-01-04", "2021-01-17"), "validation": ("2021-01-18", "2021-01-31"),
                                        "final_test": ("2021-02-01", "2021-02-14")})
    monkeypatch.setattr(fd, "WF_YEARS", ())
    monkeypatch.setattr(fd, "evaluate", lambda res, bh: tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh")))
    monkeypatch.setattr(fd, "robustness_checks", lambda dsr, nb, wf: dict(ROBUST_OK))
    monkeypatch.setattr(fd, "safe_dsr", lambda r, n, v: {"dsr": None, "undefined_reason": "mock"})
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))

    def go(market):
        monkeypatch.setattr(fd, "load", lambda cache: (market, [], [], []))
        fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
        return json.loads((tmp_path / "results.json").read_text())
    assert go(make_market(days=90, rates=ranked_rates))["verdict"] == "ZAMÍTNUTO"
    bad = make_market(days=90, rates=ranked_rates)
    t = fd.ms_of(date(2021, 1, 20)) + 8 * H
    bad["BTCUSDT"] = fd.prepare(bad["BTCUSDT"]["bars"], {k: v for k, v in bad["BTCUSDT"]["funding"].items() if k != t})
    out = go(bad)
    assert out["verdict"].startswith("NEROZHODNUTO") and "validation" in out["verdict_detail"]["benchmark_defect_periods"]


def test_K8_5_results_bind_trades_csv_hash(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(fd, "PERIODS", {"tuning": ("2021-01-04", "2021-01-17"), "validation": ("2021-01-18", "2021-01-31"),
                                        "final_test": ("2021-02-01", "2021-02-14")})
    monkeypatch.setattr(fd, "WF_YEARS", ())
    monkeypatch.setattr(fd, "load", lambda cache: (make_market(days=90, rates=ranked_rates), [], [], []))
    (tmp_path / fd.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))
    fd.main(["--outdir", str(tmp_path), "--mode", "perf"])
    r = json.loads((tmp_path / "results.json").read_text())
    assert r["trades_csv_sha256"] == fd.file_sha256(tmp_path / "trades.csv") and r["run_id"]


# ---- kolo 9, Q5: zámek spravovaný OS ----
_HOLDER = """
import sys, time
sys.path.insert(0, sys.argv[1])
from research.funding_dispersion import run as fd
with fd.RunLock(sys.argv[2]):
    print("LOCKED", flush=True)
    time.sleep(60)
"""


def _spawn_holder(tmp_path):
    import subprocess, sys as _s
    from pathlib import Path
    root = str(Path(fd.__file__).resolve().parents[2])
    p = subprocess.Popen([_s.executable, "-c", _HOLDER, root, str(tmp_path)], stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "LOCKED"
    return p


def test_K9_5_lock_held_by_other_process_refuses_and_logs(tmp_path, monkeypatch):
    import json
    p = _spawn_holder(tmp_path)
    try:
        calls = _guard(monkeypatch, market=make_market(rates=ranked_rates))
        with pytest.raises(SystemExit) as e:
            fd.main(["--outdir", str(tmp_path), "--mode", "audit"])
        assert e.value.code == 5 and calls["load"] == 0
        rec = json.loads((tmp_path / fd.CONFLICT_LOG).read_text().splitlines()[-1])
        assert json.loads(rec["holder"])["pid"] == p.pid
    finally:
        p.kill()
        p.wait()


def test_K9_5_sigkill_releases_lock_without_age_based_deletion(tmp_path, monkeypatch):
    import signal
    p = _spawn_holder(tmp_path)
    p.send_signal(signal.SIGKILL)
    p.wait()
    assert (tmp_path / fd.LOCK_FILE).exists()  # soubor zůstal (nemaže se), zámek ale jádro uvolnilo
    calls = _guard(monkeypatch, market=make_market(rates=ranked_rates))
    fd.main(["--outdir", str(tmp_path), "--mode", "audit"])  # opětovné spuštění projde
    assert calls["load"] == 1 and not (tmp_path / fd.CONFLICT_LOG).exists()


def test_K9_5_lock_code_has_no_age_based_removal():
    import inspect
    src = inspect.getsource(fd.RunLock)
    assert "unlink" not in src and "st_mtime" not in src and "getmtime" not in src
