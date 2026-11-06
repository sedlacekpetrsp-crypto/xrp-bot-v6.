"""Mechanika backtestu H-20261106-3 na syntetických datech (není důkaz ziskovosti)."""
from datetime import date

import pytest

from research.spot_led import run as sl

BAR = sl.BAR
H = sl.HOUR_MS
START = date(2021, 1, 1)
T0 = sl.ms_of(START)


def valid_decision(manifest=(), missing=(), **kw):
    """Úplný záznam rozhodnutí (kolo 6, bod 5) pro syntetické testy brány."""
    return {"semantics": "B", "evidence": "test", "decided_utc": "test", "audit_id": "run-test",
            "impl_sha256": sl.impl_fingerprint(), "data_manifest_sha256": sl.manifest_fingerprint(list(manifest), list(missing)),
            "performance_hold": False, **kw}


def flat(n_bars=2000, t0=T0):
    spot = {t0 + i * BAR: (100.0, 10.0, 5.0) for i in range(n_bars)}
    perp = {t0 + i * BAR: (100.0, 100.0) for i in range(n_bars)}
    return spot, perp


def market_with(events=None, n_bars=2000, fund=None, drop_perp=()):
    """events: {bar_index: (spot_close, taker_share, perp_close)} pro BTC; ostatní aktiva ploché."""
    m = {}
    for a in sl.ASSETS:
        spot, perp = flat(n_bars)
        if a == "BTCUSDT" and events:
            for i, (sc, sh, pc) in events.items():
                t = T0 + i * BAR
                spot[t] = (sc, 10.0, 10.0 * sh)
                perp[t] = (perp[t][0], pc)
        for i in drop_perp:
            perp.pop(T0 + i * BAR, None)
        m[a] = sl.prepare(spot, perp, fund or {})
    return m


def test_features_use_only_current_and_previous_bar():
    m = market_with({10: (100.5, 0.8, 100.0)})
    f = {T: (sh, rs, rp) for T, sh, rs, rp in m["BTCUSDT"]["features"]}
    sh, rs, rp = f[T0 + 10 * BAR]
    assert sh == pytest.approx(0.8) and rs == pytest.approx(0.005) and rp == pytest.approx(0.0)
    assert T0 not in f  # bez předchozí svíčky žádný příznak


def test_long_signal_enters_next_open_and_exits_after_hold():
    m = market_with({10: (100.5, 0.8, 100.0)})
    c = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
    assert len(c) == 1
    x = c[0]
    assert x["side"] == 1
    assert x["entry_ts"] == T0 + 11 * BAR
    assert x["exit_ts"] == T0 + 14 * BAR
    assert x["data_gap"] == 0


def test_short_signal_mirror_and_thresholds():
    m = market_with({10: (99.5, 0.2, 100.0), 50: (99.5, 0.32, 100.0)})
    c65 = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
    c70 = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.70, 15)
    assert [x["side"] for x in c65] == [-1, -1]
    assert len(c70) == 1  # podíl 0,32 není < 0,30


def test_perp_already_moved_blocks_signal():
    m = market_with({10: (100.5, 0.8, 100.2)})  # r_perp +0,2 % ≥ +0,1 %
    assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15) == []


def test_no_overlap_per_asset():
    # 1. obchod: signál 10, vstup 11, výstup 14. Signál 11 (vstup 12) během pozice ⇒ ignorován;
    # signál 13 má vstup 14 = výstup prvního ⇒ povolen.
    m = market_with({10: (100.5, 0.8, 100.0), 11: (101.0, 0.8, 100.0), 13: (100.5, 0.8, 100.0)})
    c = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
    assert [x["signal_ts"] for x in c] == [T0 + 10 * BAR, T0 + 13 * BAR]
    assert c[1]["entry_ts"] == c[0]["exit_ts"]


def test_missing_entry_bar_drops_signal_and_missing_exit_flags_gap():
    m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=(11,))
    assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15) == []
    m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=(14,))
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
    assert x["exit_ts"] == T0 + 15 * BAR and x["data_gap"] == 1


def test_funding_only_strictly_inside_holding():
    # vstup 11*5m = 00:55, výstup 01:10 (15 min) ⇒ událost 01:00 uvnitř; 30 min držení ⇒ stejně jedna
    fund = {T0 + H: 0.001, T0: 0.5, T0 + 2 * H: 0.5}
    m = market_with({10: (100.5, 0.8, 100.0)}, fund=fund)
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
    assert x["funding_unit"] == pytest.approx(-0.001 * 100.0)  # long platí kladnou sazbu
    # událost přesně v čase vstupu se nezapočte
    m2 = market_with({11: (100.5, 0.8, 100.0)}, fund={T0 + H: 0.001})
    y = sl.candidates(m2["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
    assert y["entry_ts"] == T0 + H and y["funding_unit"] == 0.0


def test_prefix_invariance():
    ev = {10: (100.5, 0.8, 100.0), 300: (99.5, 0.2, 100.0)}
    short = sl.candidates(market_with(ev, n_bars=1000)["BTCUSDT"], "BTCUSDT", T0, T0 + 900 * BAR, 0.65, 15)
    long_ = sl.candidates(market_with(ev, n_bars=3000)["BTCUSDT"], "BTCUSDT", T0, T0 + 900 * BAR, 0.65, 15)
    assert short == long_


def test_costs_scale_and_equity_reconciles():
    ev = {10: (100.5, 0.8, 100.0), 300: (99.5, 0.2, 100.0)}
    m = market_with(ev, n_bars=2000)
    end = date(2021, 1, 6)
    costs = {}
    for mult in (1, 2, 3):
        trades, curve = sl.simulate(m, START, end, 0.65, 15, mult)
        costs[mult] = sum(t["costs"] for t in trades) / sum(t["notional"] for t in trades)
        assert curve[end] == pytest.approx(sl.START_EQUITY + sum(t["net_pnl"] for t in trades))
    assert costs[2] == pytest.approx(2 * costs[1]) and costs[3] == pytest.approx(3 * costs[1])
    # plochá cena ⇒ každý obchod ztratí právě round-trip náklady 2 × 0,115 %
    trades, _ = sl.simulate(m, START, end, 0.65, 15, 1)
    assert trades[0]["net_pnl"] == pytest.approx(-1000 * 2 * (sl.FEE + sl.SLIP))


def test_exit_must_stay_inside_period():
    m = market_with({10: (100.5, 0.8, 100.0)})
    assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 13 * BAR, 0.65, 15) == []


def test_neighbors_and_gap_audit():
    assert set(sl.neighbors(0.65, 15)) == {(0.65, 30), (0.70, 15)}
    m = market_with(drop_perp=(5, 6))
    a = sl.gap_audit(m["BTCUSDT"])
    assert a["perp_missing_5m"] == 2 and a["spot_only"] == 2


# ---- oponentura ChatGPT kolo 2, bod G a společné opravy (B&H funding, nedefinované DSR, latence) ----
def test_G_overnight_position_enters_daily_mtm():
    i_sig = 24 * 12 - 3  # signál 23:45, vstup 23:50, výstup 00:05 dalšího dne
    m = market_with({i_sig: (100.5, 0.8, 100.0)}, n_bars=3 * 288)
    t_last = T0 + (24 * 12 - 1) * BAR  # svíčka 23:55 dne 1
    m["BTCUSDT"]["perp"][t_last] = (100.0, 110.0)  # close 23:55 = 110
    trades, curve = sl.simulate(m, START, date(2021, 1, 2), 0.65, 15, 1)
    tr = trades[0]
    assert tr["entry_ts"] < T0 + sl.DAY_MS < tr["exit_ts"]
    expected = sl.START_EQUITY + tr["qty"] * (110.0 - 100.0) - tr["cost_in"]
    assert curve[START] == pytest.approx(expected)
    assert curve[date(2021, 1, 2)] == pytest.approx(sl.START_EQUITY + tr["net_pnl"])


def test_G_exit_delay_is_bounded():
    # mezera 30 min ⇒ první dostupný open, data_gap 1
    m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=range(14, 20))
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
    assert x["exit_ts"] == T0 + 20 * BAR and x["data_gap"] == 1
    # mezera > 60 min ⇒ DATA_GAP 2, cena = poslední close před plánovaným výstupem, čas = plán + 60 min
    m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=range(14, 40))
    m["BTCUSDT"]["perp"][T0 + 13 * BAR] = (100.0, 97.0)
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)[0]
    assert x["data_gap"] == 2 and x["exit"] == 97.0 and x["exit_ts"] == T0 + 14 * BAR + sl.MAX_EXIT_DELAY_MS


def test_G_no_exit_beyond_period_end_time_based():
    m = market_with({10: (100.5, 0.8, 100.0)})
    end = T0 + 14 * BAR + sl.MAX_EXIT_DELAY_MS  # plán + max. zpoždění = konec ⇒ nebrat
    assert sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, end, 0.65, 15) == []
    assert len(sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, end + BAR, 0.65, 15)) == 1


def test_G_simultaneous_entries_independent_of_symbol_order(monkeypatch):
    def mk():
        m = {}
        for a in sl.ASSETS:
            spot, perp = flat()
            t = T0 + 10 * BAR
            spot[t] = (100.5, 10.0, 8.0)
            perp[T0 + 14 * BAR] = (101.0 if a == "ETHUSDT" else 99.0, 100.0)
            m[a] = sl.prepare(spot, perp, {})
        return m
    m = mk()
    a1, _ = sl.simulate(m, START, date(2021, 1, 6), 0.65, 15, 1)
    monkeypatch.setattr(sl, "ASSETS", tuple(reversed(sl.ASSETS)))
    a2, _ = sl.simulate(m, START, date(2021, 1, 6), 0.65, 15, 1)
    key = lambda t: (t["asset"], t["notional"], round(t["net_pnl"], 9))
    assert sorted(map(key, a1)) == sorted(map(key, a2))
    assert all(t["notional"] == pytest.approx(1000.0) for t in a1) and len(a1) == 3


def test_latency_sensitivity_enters_one_bar_later():
    m = market_with({10: (100.5, 0.8, 100.0)})
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15, delay_bars=1)[0]
    assert x["entry_ts"] == T0 + 12 * BAR and x["exit_ts"] == T0 + 15 * BAR


def test_buy_hold_accounts_funding_sign():
    res = {}
    for r in (0.0, 0.01, -0.01):
        fund = {T0 + k * 8 * H: r for k in range(1, 6)}
        m = market_with(n_bars=2000, fund=fund)
        res[r] = sl.buy_hold(m, START, date(2021, 1, 6), 1)
    assert res[0.01]["net_pnl"] < res[0.0]["net_pnl"] < res[-0.01]["net_pnl"]
    assert res[0.01]["funding"] == pytest.approx(-0.01 * sl.START_EQUITY * (1 - (sl.FEE + sl.SLIP)) * 5)


def test_undefined_dsr_is_null_not_zero():
    out = sl.safe_dsr([0.0] * 731, 159, 0.5)
    assert out["dsr"] is None and out["undefined_reason"]


# ---- oponentura ChatGPT kolo 3 ----
def _overnight_market(fund=None, drop=()):
    i_sig = 24 * 12 - 3  # signál 23:45, vstup 23:50, výstup 00:05
    m = market_with({i_sig: (100.5, 0.8, 100.0)}, n_bars=3 * 288, fund=fund, drop_perp=drop)
    return m


def test_K3_2_midnight_funding_belongs_to_new_day_consistently():
    m = _overnight_market(fund={T0 + sl.DAY_MS: 0.01})
    trades, curve = sl.simulate(m, START, date(2021, 1, 2), 0.65, 15, 1)
    tr = trades[0]
    assert curve[START] == pytest.approx(9998.85)  # ocenění před událostmi v 00:00
    assert curve[date(2021, 1, 2)] == pytest.approx(sl.START_EQUITY + tr["net_pnl"])
    assert tr["funding"] == pytest.approx(-0.01 * tr["qty"] * 100.0)
    # benchmark se stejnou konvencí: funding v 00:00 dne 2 se projeví až ve dni 2
    bh_m = market_with(n_bars=3 * 288, fund={T0 + sl.DAY_MS: 0.01})
    b1 = sl.buy_hold(bh_m, START, START, 1)
    b2 = sl.buy_hold(bh_m, START, date(2021, 1, 2), 1)
    assert b1["funding"] == 0.0 and b2["funding"] < 0


def test_K3_2_exit_exactly_at_midnight_and_entry_at_midnight():
    # vstup 23:45, výstup přesně 00:00 (15 min): den 1 = ocenění otevřené pozice, realizace ve dni 2
    i_sig = 24 * 12 - 4
    m = market_with({i_sig: (100.5, 0.8, 100.0)}, n_bars=3 * 288)
    m["BTCUSDT"]["perp"][T0 + (24 * 12 - 1) * BAR] = (100.0, 105.0)
    trades, curve = sl.simulate(m, START, date(2021, 1, 2), 0.65, 15, 1)
    tr = trades[0]
    assert tr["exit_ts"] == T0 + sl.DAY_MS
    assert curve[START] == pytest.approx(sl.START_EQUITY + tr["qty"] * 5.0 - tr["cost_in"])
    assert curve[date(2021, 1, 2)] == pytest.approx(sl.START_EQUITY + tr["net_pnl"])
    # vstup přesně v 00:00 patří novému dni: den 1 beze změny
    m2 = market_with({24 * 12 - 1: (100.5, 0.8, 100.0)}, n_bars=3 * 288)
    t2, c2 = sl.simulate(m2, START, date(2021, 1, 2), 0.65, 15, 1)
    assert t2[0]["entry_ts"] == T0 + sl.DAY_MS and c2[START] == sl.START_EQUITY


def test_K3_3_day_close_never_uses_future_price():
    perp = {T0 + sl.DAY_MS + k * BAR: (100.0, 100.0 if k == 0 else 200.0) for k in range(2 * 288)}
    m = sl.prepare({}, perp, {})
    assert sl.day_close(m, date(2021, 1, 1)) is None
    assert sl.day_close(sl.prepare({}, {}, {}), date(2021, 1, 1)) is None
    p, age = sl.day_close(m, date(2021, 1, 2))
    assert p == 200.0 and age == 0


def test_K3_3_benchmark_asset_unavailable_at_start_is_cash():
    m = market_with(n_bars=2000)
    late = {t + 3 * sl.DAY_MS: v for t, v in m["XRPUSDT"]["perp"].items()}  # první svíčka až za koncem období
    m["XRPUSDT"] = sl.prepare(m["XRPUSDT"]["spot"], late, {})
    b = sl.buy_hold(m, START, date(2021, 1, 2), 1)
    assert b["unavailable_at_start"] == ["XRPUSDT"]
    # 2/3 v aktivech (ploché ceny) − náklady, 1/3 hotovost
    c = sl.FEE + sl.SLIP
    assert b["net_pnl"] == pytest.approx(-(2 / 3) * sl.START_EQUITY * (1 - (1 - c) ** 2), abs=1e-3)


def test_K3_4_funding_price_fallback_is_flagged_and_aged():
    m = _overnight_market(fund={T0 + sl.DAY_MS: 0.01}, drop=(288,))
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
    assert x["funding_price_fallbacks"] == 1 and x["funding_price_max_age_min"] == 0.0
    assert x["unevaluable"] == 0
    # náhrada starší než 60 min ⇒ nehodnotitelné: svíčky 23:55–01:00 chybí, výstup zpožděn na 01:05 (data_gap 1),
    # funding v 01:00 (1h interval) by se počítal z close 23:55 ⇒ stáří 65 min
    fund = {T0 + sl.DAY_MS: (0.01, 1.0), T0 + sl.DAY_MS + H: (0.01, 1.0)}
    m = _overnight_market(fund=fund, drop=range(287, 301))
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
    assert x["data_gap"] == 1 and x["exit_ts"] == T0 + sl.DAY_MS + H + BAR
    assert x["funding_price_fallbacks"] == 2 and x["funding_price_max_age_min"] == 65.0 and x["unevaluable"] == 1


def test_K3_4_missing_funding_event_is_flagged_not_zero():
    # interval 8 h, ale událost 00:00 chybí (je jen 16:00 předchozího dne a 08:00) ⇒ mezera v úplnosti
    fund = {T0 + 16 * H: (0.0001, 8.0), T0 + 32 * H: (0.0001, 8.0)}
    m = _overnight_market(fund=fund)
    x = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
    assert x["funding_gaps"] == 1 and x["funding_unit"] == 0.0
    ok = _overnight_market(fund={T0 + 16 * H: 0.0001, T0 + 24 * H: 0.0001, T0 + 32 * H: 0.0001})
    y = sl.candidates(ok["BTCUSDT"], "BTCUSDT", T0, T0 + 3 * sl.DAY_MS, 0.65, 15)[0]
    assert y["funding_gaps"] == 0 and y["funding_unit"] != 0.0


# ---- dodatek 3: zámek výkonnosti bez rozhodnutí o sémantice ----
def test_gate_refuses_performance_without_semantics_decision(tmp_path, monkeypatch):
    import json
    called = []
    monkeypatch.setattr(sl, "load", lambda cache: called.append(1) or ({}, [], [], []))
    with pytest.raises(SystemExit) as e:
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])
    assert e.value.code == 3 and called == []
    ok = valid_decision()
    for bad in ({**ok, "semantics": "C"}, {"semantics": "B"}, {**ok, "semantics": "A"},
                {**ok, "performance_hold": True}, {k: v for k, v in ok.items() if k != "performance_hold"}):
        (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(bad))
        assert sl.semantics_gate(tmp_path)[0] is False
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(ok))
    assert sl.semantics_gate(tmp_path) == (True, "ok")


def test_committed_decision_keeps_performance_blocked():
    from pathlib import Path
    import json
    d = json.loads((Path(sl.__file__).parent / sl.SEMANTICS_FILE).read_text())
    assert d["semantics"] == "B" == sl.IMPLEMENTED_SEMANTICS and d["performance_hold"] is True
    assert sl.semantics_gate(Path(sl.__file__).parent)[0] is False


def test_semantics_B_mid_period_change_tolerated_and_real_gap_flagged():
    # 8 h → 4 h (záznam 20:00 nese 4) → 2 h se změnou uprostřed úseku (00:00 → 04:00 rozestup 4, záznam nese 2)
    seq = [(0, 8), (8, 8), (16, 8), (20, 4), (24, 4), (28, 2), (30, 2), (32, 2)]
    f = {T0 + h * H: (0.0001, float(iv)) for h, iv in seq}
    m = sl.prepare({}, {}, f)
    assert sl.funding_chain_gaps(m, T0, T0 + 32 * H) == 0
    del f[T0 + 30 * H]
    assert sl.funding_chain_gaps(sl.prepare({}, {}, f), T0, T0 + 32 * H) == 1


def test_audit_only_mode_writes_funding_audit(tmp_path, monkeypatch):
    import json
    fund = {T0 + k * 8 * H: (0.0001, 8.0) for k in range(3)}
    fund.update({T0 + 16 * H + k * 4 * H: (0.0001, 4.0) for k in range(1, 4)})
    m = {a: sl.prepare(*flat(), fund) for a in sl.ASSETS}
    monkeypatch.setattr(sl, "load", lambda cache: (m, [], [], []))
    sl.main(["--outdir", str(tmp_path), "--audit-only"])
    a = json.loads((tmp_path / "data_audit.json").read_text())["funding"]["BTCUSDT"]
    assert not (tmp_path / "results.json").exists()
    assert len(a["interval_transitions"]) == 1 and a["interval_transitions"][0]["spacing_h"] == 4.0
    assert a["spacing_mismatch_semantics_A"] == 1 and a["spacing_mismatch_semantics_B"] == 0
    assert a["spacing_mismatch_semantics_B_tolerant_implemented"] == 0


# ---- kolo 6 (oponentura kol 4–6): testy DOKAZUJÍCÍ OPRAVU ----
C = sl.FEE + sl.SLIP


def test_K6_2_late_entry_excludes_funding_exactly_at_entry():
    """Reprodukce z oponentury: všechna 3 aktiva mají první svíčku až v 01:00, jediný funding právě v 01:00."""
    bh = sl.buy_hold(market_with(fund={T0 + H: 0.01}, drop_perp=range(12)), START, START, 1)
    assert set(bh["entry_utc"].values()) == {"2021-01-01T01:00:00+00:00"}
    assert bh["funding"] == 0.0
    assert bh["net_pnl"] == pytest.approx(-sl.START_EQUITY * (1 - (1 - C) ** 2), abs=1e-4)  # ≈ −22,9868, jen náklady


def test_K6_2_mixed_entry_times_per_asset():
    fund = {T0 - 7 * H: 0.0, T0 + H: 0.01, T0 + 9 * H: 0.0, T0 + 17 * H: 0.0}
    m = {}
    for a in sl.ASSETS:
        spot, perp = flat()
        if a == "ETHUSDT":  # ETH koupen až v 01:00 ⇒ událost 01:00 je přesně ve vstupu, nepočítá se
            for i in range(12):
                perp.pop(T0 + i * BAR)
        m[a] = sl.prepare(spot, perp, fund)
    bh = sl.buy_hold(m, START, START, 1)
    assert bh["entry_utc"]["BTCUSDT"] == "2021-01-01T00:00:00+00:00" and bh["entry_utc"]["ETHUSDT"] == "2021-01-01T01:00:00+00:00"
    q = sl.START_EQUITY / 3 * (1 - C) / 100
    assert bh["funding"] == pytest.approx(-2 * 0.01 * q * 100)  # platí jen BTC a XRP


def test_K6_2_funding_window_entry_inside_exit():
    m = sl.prepare({}, {}, {T0 + k * H: 0.001 for k in range(0, 25, 8)})
    assert sl.funding_window(m, T0, T0 + 16 * H) == [T0 + 8 * H]  # vstup 00:00 a výstup 16:00 vyloučeny
    assert sl.funding_completeness(m, T0, T0 + 16 * H) == {"discontinuities": 0, "missing_events": 0, "unknown_coverage": False}
    # benchmark: událost přesně v okamžiku prodeje (půlnoc po posledním dni) se neúčtuje
    fund = {T0 - 8 * H + k * 8 * H: 0.01 for k in range(5)}  # 16:00 den předem … 00:00 dalšího dne
    bh = sl.buy_hold(market_with(fund=fund), START, START, 1)
    q = sl.START_EQUITY / 3 * (1 - C) / 100
    assert bh["funding"] == pytest.approx(-3 * 2 * 0.01 * q * 100)  # jen 08:00 a 16:00
    assert bh["funding_missing_events"] == 0


def test_K6_1_benchmark_gap_counted_three_assets():
    fund = {T0 - 8 * H + k * 8 * H: 0.01 for k in range(5)}
    del fund[T0 + 8 * H]
    bh = sl.buy_hold(market_with(fund=fund), START, START, 1)
    assert (bh["funding_missing_events"], bh["funding_discontinuities"], bh["funding_unknown_coverage_assets"]) == (3, 3, 0)
    unk = sl.buy_hold(market_with(fund={T0 + 8 * H: 0.01, T0 + 16 * H: 0.01}), START, START, 1)
    assert unk["funding_unknown_coverage_assets"] == 3


def test_K6_3_benchmark_fresh_fallback_is_blocking_defect():
    fund = {T0 - 8 * H + k * 8 * H: 0.01 for k in range(5)}
    m = market_with(fund=fund, drop_perp=(96,))  # chybí svíčka 08:00, předchozí close je stará 0 min
    bh = sl.buy_hold(m, START, START, 1)
    assert bh["funding_price_fallbacks"] == 3 and bh["stale_valuations"] == 0
    flags = {k: 0 for k in sl.DATA_DEFECTS} | {"benchmark_funding_price_fallbacks": 3}
    v, blocking = sl.final_verdict(True, True, {"r": True}, flags, 1.0)
    assert v.startswith("NEROZHODNUTO") and blocking == {"benchmark_funding_price_fallbacks": 3}


def test_K6_3_registry_complete_unknown_raises_informational_ok():
    m = market_with({10: (100.5, 0.8, 100.0)})
    res = {p: {"x1": sl.run(m, START, date(2021, 1, 5), 1, 0.65, 15, "t")[0]} for p in sl.PERIODS}
    bh = {p: {"x1": sl.buy_hold(m, START, date(2021, 1, 5), 1)} for p in sl.PERIODS}
    flags = sl.defect_flags(res, bh)
    assert set(flags) == set(sl.DATA_DEFECTS)
    with pytest.raises(KeyError):
        sl.blocking_defects({**flags, "nove": 1})
    info = {k: 0 for k in sl.DATA_DEFECTS} | {"data_gap_exits_within_limit": 4}
    assert sl.final_verdict(True, False, {"r": True}, info, 1.0) == ("KANDIDÁT NA FORWARD PAPER", {})


def test_K6_4_unfilled_entry_recorded_with_reason_and_notional():
    """Reprodukce z oponentury: dřív trades = 0 a žádná evidence."""
    m = market_with({10: (100.5, 0.8, 100.0)}, drop_perp=(11,))
    r, trades, _ = sl.run(m, START, date(2021, 1, 5), 1, 0.65, 15, "t")
    assert r["trades"] == 0 and r["unfilled_entries"] == 1
    assert r["unfilled_entry_records"] == [{"asset": "BTCUSDT", "side": 1, "signal_utc": "2021-01-01T00:50:00+00:00",
                                            "entry_utc": "2021-01-01T00:55:00+00:00", "planned_notional": 1000.0,
                                            "reason": "missing_entry_candle"}]


def test_K6_4_mixed_unfilled_does_not_change_other_trades(monkeypatch):
    m = market_with({10: (100.5, 0.8, 100.0), 14: (100.5, 0.8, 100.0), 60: (99.5, 0.2, 100.0)}, drop_perp=(11,))
    r, trades, _ = sl.run(m, START, date(2021, 1, 5), 1, 0.65, 15, "t")
    assert r["unfilled_entries"] == 1 and [t["entry_ts"] for t in trades] == [T0 + 15 * BAR, T0 + 61 * BAR]
    orig = sl.candidates
    monkeypatch.setattr(sl, "candidates", lambda *a, **k: [x for x in orig(*a, **k) if not x.get("unfilled")])
    _, without, _ = sl.run(m, START, date(2021, 1, 5), 1, 0.65, 15, "t")
    key = lambda t: (t["asset"], t["entry_ts"], t["exit_ts"], round(t["qty"], 12), round(t["net_pnl"], 12))
    assert [key(t) for t in trades] == [key(t) for t in without]  # evidence nezměnila obchody ani sizing


# ---- kolo 6, bod 5: brána výkonnosti ----
def _boom(*a, **k):
    raise AssertionError("simulace nesmí být zavolána")


def _guard(monkeypatch, market=None, manifest=()):
    calls = {"load": 0}

    def load(cache):
        calls["load"] += 1
        return market or {}, list(manifest), [], []
    monkeypatch.setattr(sl, "load", load)
    for f in ("simulate", "simulate_full", "run", "buy_hold"):
        monkeypatch.setattr(sl, f, _boom)
    return calls


@pytest.mark.parametrize("decision", [None, "{nejson", {"semantics": "B"}, valid_decision(performance_hold=True),
                                      valid_decision(audit_id=""), valid_decision(impl_sha256="0" * 64),
                                      valid_decision(semantics="A")])
def test_K6_5_invalid_decision_no_load_no_sim_no_metrics(tmp_path, monkeypatch, decision):
    import json
    if decision is not None:
        (tmp_path / sl.SEMANTICS_FILE).write_text(decision if isinstance(decision, str) else json.dumps(decision))
    calls = _guard(monkeypatch)
    with pytest.raises(SystemExit) as e:
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])
    assert e.value.code == 3 and calls["load"] == 0
    assert not any((tmp_path / f).exists() for f in ("results.json", "trades.csv", "data_source.json"))


def test_K6_5_changed_data_loads_but_never_simulates(tmp_path, monkeypatch):
    import json
    audited = [{"url": "u1", "sha256": "a" * 64, "rows": 1}]
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision(manifest=audited)))
    calls = _guard(monkeypatch, manifest=[{"url": "u1", "sha256": "b" * 64, "rows": 1}])
    with pytest.raises(SystemExit) as e:
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])
    assert e.value.code == 3 and calls["load"] == 1
    assert not any((tmp_path / f).exists() for f in ("results.json", "trades.csv", "data_source.json"))


def test_K6_5_valid_gate_reaches_simulation_with_mocked_performance(tmp_path, monkeypatch):
    import json
    audited = [{"url": "u1", "sha256": "a" * 64, "rows": 1}]
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision(manifest=audited)))
    _guard(monkeypatch, market=market_with(), manifest=audited)

    class Reached(Exception):
        pass

    def reached(*a, **k):
        raise Reached
    monkeypatch.setattr(sl, "run", reached)
    with pytest.raises(Reached):
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])


def test_K6_5_audit_never_simulates_and_disowns_old_results(tmp_path, monkeypatch):
    import json
    (tmp_path / "trades.csv").write_text("stary")
    _guard(monkeypatch, market=market_with())
    sl.main(["--outdir", str(tmp_path), "--mode", "audit"])
    man = json.loads((tmp_path / sl.AUDIT_MANIFEST_FILE).read_text())
    assert man["preexisting_performance_files_not_from_this_run"] == ["trades.csv"]
    assert "trades.csv" not in man["produced_by_this_run"] and (tmp_path / "trades.csv").read_text() == "stary"


@pytest.mark.parametrize("text", ["BACKTEST 2026", "", "audit"])
def test_K6_5_unknown_mode_refused(tmp_path, monkeypatch, text):
    req = tmp_path / "RUN_REQUEST"
    req.write_text(text)
    calls = _guard(monkeypatch)
    with pytest.raises(SystemExit) as e:
        sl.main(["--outdir", str(tmp_path), "--request-file", str(req)])
    assert e.value.code == 4 and calls["load"] == 0


def test_K6_5_missing_or_conflicting_mode_refused(tmp_path, monkeypatch):
    calls = _guard(monkeypatch)
    for argv in ([], ["--audit-only", "--mode", "perf"]):
        with pytest.raises(SystemExit) as e:
            sl.main(["--outdir", str(tmp_path), *argv])
        assert e.value.code == 4
    assert calls["load"] == 0


def test_K6_5_committed_request_is_audit_and_decision_still_blocks():
    from pathlib import Path
    here = Path(sl.__file__).parent
    assert sl.mode_from_request(here / "RUN_REQUEST") == "audit"
    ok, why = sl.semantics_gate(here)
    assert ok is False and "performance_hold" in why


def test_K6_integration_final_verdict_blocked_by_benchmark_fallback_else_candidate(tmp_path, monkeypatch):
    """Celá větev main → buy_hold → defect_flags → final_verdict → results.json; kritéria, robustnost a latence
    vynuceně splněné (mock), rozhoduje jen datová brána."""
    import json
    monkeypatch.setattr(sl, "PERIODS", {"tuning": ("2021-01-01", "2021-01-02"), "validation": ("2021-01-03", "2021-01-04"),
                                        "final_test": ("2021-01-05", "2021-01-06")})
    monkeypatch.setattr(sl, "WF_YEARS", ())
    monkeypatch.setattr(sl, "evaluate", lambda res, bh: ({"A": True}, {"B": True}))
    monkeypatch.setattr(sl, "robustness_checks", lambda dsr, nb, wf: {"mock": True})
    monkeypatch.setattr(sl, "safe_dsr", lambda r, n, v: {"dsr": None, "undefined_reason": "mock"})
    monkeypatch.setattr(sl, "latency_info", lambda *a: {"validation": {"x2": {"net_pnl": 1.0}}})
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))
    fund = {T0 - 8 * H + k * 8 * H: 0.0001 for k in range(25)}

    def go(market):
        monkeypatch.setattr(sl, "load", lambda cache: (market, [], [], []))
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])
        return json.loads((tmp_path / "results.json").read_text())
    clean = go(market_with(fund=fund))
    assert clean["verdict"] == "KANDIDÁT NA FORWARD PAPER" and clean["blocking_data_defects"] == {}
    bad = go(market_with(fund=fund, drop_perp=(sl.DAY_MS * 2 // BAR + 96,)))  # 3. 1. 08:00: chybí svíčka v čase fundingu
    assert bad["verdict"].startswith("NEROZHODNUTO")
    assert bad["blocking_data_defects"] == {"benchmark_funding_price_fallbacks": 3}
