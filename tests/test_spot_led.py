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
            "ops_sha256": sl.ops_fingerprint(),
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
    a = json.loads((sl.latest_audit_dir(tmp_path) / "data_audit.json").read_text())["funding"]["BTCUSDT"]
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
    v, blocking, _ = sl.final_verdict({"A1_sharpe_dd": True}, {"B1_val_x2_profit_pf": True}, {"r": True}, flags, {}, 1.0)
    assert v.startswith("NEROZHODNUTO") and blocking == {"benchmark_funding_price_fallbacks": 3}


def test_K6_3_registry_complete_unknown_raises_informational_ok():
    m = market_with({10: (100.5, 0.8, 100.0)})
    res = {p: {"x1": sl.run(m, START, date(2021, 1, 5), 1, 0.65, 15, "t")[0]} for p in sl.PERIODS}
    bh = {p: {"x1": sl.buy_hold(m, START, date(2021, 1, 5), 1)} for p in sl.PERIODS}
    flags = sl.defect_flags(res, bh, m)
    assert set(flags) | {"walk_forward_defects", "neighbor_defects"} == set(sl.DATA_DEFECTS)
    with pytest.raises(KeyError):
        sl.blocking_defects({**flags, "nove": 1})
    info = {k: 0 for k in sl.DATA_DEFECTS} | {"data_gap_exits_within_limit": 4}
    assert sl.final_verdict({"A1_sharpe_dd": True}, {"B1_val_x2_profit_pf": False}, {"r": True}, info, {}, 1.0)[:2] == \
        ("KANDIDÁT NA FORWARD PAPER", {})


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
    man = json.loads((sl.latest_audit_dir(tmp_path) / sl.AUDIT_MANIFEST_FILE).read_text())
    assert man["outdir_performance_files_not_from_this_run"] == ["trades.csv"]
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
    monkeypatch.setattr(sl, "PERIODS", {"tuning": ("2021-01-02", "2021-01-02"), "validation": ("2021-01-03", "2021-01-04"),
                                        "final_test": ("2021-01-05", "2021-01-06")})
    monkeypatch.setattr(sl, "WF_YEARS", ())
    monkeypatch.setattr(sl, "evaluate", lambda res, bh: ({"A": True}, {"B": True}))
    monkeypatch.setattr(sl, "robustness_checks", lambda dsr, nb, wf: {"mock": True})
    monkeypatch.setattr(sl, "safe_dsr", lambda r, n, v: {"dsr": None, "undefined_reason": "mock"})
    monkeypatch.setattr(sl, "latency_info", lambda *a: {"validation": {"x2": {"net_pnl": 1.0}}})
    monkeypatch.setattr(sl, "robustness_context", lambda *a: {"dsr": 0.99, "dsr_defects": {}, "neighbors": {"n": (1.0, {})},
                                                              "wf": {y: (1.0, 5, {}) for y in "abc"}})
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
    assert bad["blocking_data_defects"]["benchmark_funding_price_fallbacks"] == 3
    assert bad["blocking_data_defects"]["signal_bars_lost_to_gaps"] == 6  # kolo 9: chybějící svíčka ruší i signály (3 aktiva × 2)


# ---- kolo 8: rozhodovací logika, otisk implementace, hranice fundingu, atomické audity ----
CRIT_A = ("A1_sharpe_dd", "A2_trades_ge_30", "A3_x2_pf_profit", "A4_wo_top3", "A5_final_x2")
CRIT_B = ("B1_val_x2_profit_pf", "B2_dd_le_0_6_bh", "B3_final_x2_profit", "B4_val_wo_top3", "B5_trades_ge_20",
          "B6_tuning_x1_profit")
ROBUST_OK = {"dsr_ge_0_95": True, "neighbors_val_x2_profit": True, "walk_forward_ge_3_of_4": True}
NO_FLAGS = {k: 0 for k in sl.DATA_DEFECTS}
BAD_VAL = {"validation": {"benchmark_funding_missing_events": 1}}


def tracks(fail=()):
    return ({c: c not in fail for c in CRIT_A}, {c: c not in fail for c in CRIT_B})


def test_K8_1_dependency_map_matches_evaluate_by_perturbation():
    base = {"sharpe": 1.0, "max_drawdown_pct": 10.0, "trades": 40, "profit_factor": 1.5, "net_pnl": 100.0,
            "net_without_top3": 50.0}
    res = {p: {f"x{m}": dict(base) for m in (1, 2, 3)} for p in sl.PERIODS}
    found = {c: set() for c in CRIT_A + CRIT_B}
    for p in sl.PERIODS:
        for alt in ({"sharpe": 5.0, "max_drawdown_pct": 1.0}, {"sharpe": -5.0, "max_drawdown_pct": 99.0}):
            bh = {q: {f"x{m}": {"sharpe": 0.5, "max_drawdown_pct": 20.0} for m in (1, 2, 3)} for q in sl.PERIODS}
            ref = {**sl.evaluate(res, bh)[0], **sl.evaluate(res, bh)[1]}
            bh[p] = {f"x{m}": dict(alt) for m in (1, 2, 3)}
            new = {**sl.evaluate(res, bh)[0], **sl.evaluate(res, bh)[1]}
            found.update({c: found[c] | {p} for c in ref if ref[c] != new[c]})
    assert {c: tuple(sorted(v)) for c, v in found.items()} == {c: tuple(sorted(v)) for c, v in sl.BENCHMARK_DEPENDENCY.items()}


def test_K8_1_verdict_matrix():
    a, b = tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh"))
    assert sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, {})[0] == "ZAMÍTNUTO"                        # čistá data
    assert sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)[0].startswith("NEROZHODNUTO")       # relevantní vada
    a, b = tracks(fail=("A1_sharpe_dd", "A2_trades_ge_30", "B2_dd_le_0_6_bh", "B5_trades_ge_20"))
    assert sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)[0] == "ZAMÍTNUTO"                   # nezávislý důvod
    a, b = tracks(fail=("A5_final_x2", "B3_final_x2_profit"))
    assert sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)[0] == "ZAMÍTNUTO"                   # vada v jiném období
    a, b = tracks(fail=("A1_sharpe_dd", "A5_final_x2", "B2_dd_le_0_6_bh"))
    v, _, d = sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, BAD_VAL)
    assert (d["track_a"], d["track_b"]) == ("fail", "unknown") and v.startswith("NEROZHODNUTO")     # kombinace
    a, b = tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh"))
    assert sl.final_verdict(a, b, {**ROBUST_OK, "dsr_ge_0_95": False}, NO_FLAGS, BAD_VAL)[0] == "ZAMÍTNUTO"
    assert sl.final_verdict({"X": False}, {"Y": False}, ROBUST_OK, NO_FLAGS, BAD_VAL)[0].startswith("NEROZHODNUTO")
    a, b = tracks()
    assert sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, {}, 1.0)[0] == "KANDIDÁT NA FORWARD PAPER"
    assert sl.final_verdict(a, b, ROBUST_OK, NO_FLAGS, {}, -1.0)[0].startswith("NEROZHODNUTO")     # latence


def _src():
    from pathlib import Path
    root = Path(sl.__file__).resolve().parents[2]
    return {r: (root / r).read_text() for r in sl.FINGERPRINT_SOURCES}


def test_K8_2_fingerprint_ignores_comments_docstrings_but_not_code_or_constants():
    src = _src()
    run_py, dsr_py = sl.FINGERPRINT_SOURCES[:2]
    base = sl.code_fingerprint(src)
    assert base == sl.impl_fingerprint()
    assert sl.code_fingerprint({**src, run_py: src[run_py].replace("# limit souborů GitHubu", "# jiný")}) == base
    assert sl.code_fingerprint({**src, run_py: src[run_py].replace('"""→ [(ts, open, close)]"""', '"""x"""')}) == base
    for old, new in (("FEE, SLIP = 0.00095, 0.0002", "FEE, SLIP = 0.00095, 0.0003"),
                     ("FRACTION = 0.10", "FRACTION = 0.11"),
                     ("MAX_EXIT_DELAY_MS = 60 * 60_000", "MAX_EXIT_DELAY_MS = 61 * 60_000"),
                     ("return fts[bisect.bisect_right(fts, entry)", "return fts[bisect.bisect_left(fts, entry)"),
                     ('"benchmark_funding_price_fallbacks": "blocking"', '"benchmark_funding_price_fallbacks": "informational"'),
                     ("candidate_extra_ok=latency_val_x2_net > 0", "candidate_extra_ok=True")):
        assert old in src[run_py], old
        assert sl.code_fingerprint({**src, run_py: src[run_py].replace(old, new, 1)}) != base, old
    assert sl.code_fingerprint({**src, dsr_py: src[dsr_py] + "\nX_NEW = 1\n"}) != base


def test_K8_2_changed_code_invalidates_previous_decision(tmp_path):
    import json
    src = _src()
    old_fp = sl.code_fingerprint({**src, sl.FINGERPRINT_SOURCES[0]: src[sl.FINGERPRINT_SOURCES[0]].replace(
        "FRACTION = 0.10", "FRACTION = 0.12")})
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision(impl_sha256=old_fp)))
    ok, why = sl.semantics_gate(tmp_path)
    assert ok is False and "impl_sha256" in why


def test_K8_3_strategy_entry_and_exit_exactly_at_funding():
    # signál 11 ⇒ vstup 12 (01:00), výstup po 15 min ve 01:15; druhý: vstup 01:45 → výstup 02:00 přesně ve fundingu
    fund = {T0 - 7 * H + k * H: 0.01 for k in range(40)}  # hodinový funding (stejný interval 8 h jen pro sazbu nevadí)
    fund = {t: (0.01, 1.0) for t in fund}
    m = market_with({11: (100.5, 0.8, 100.0), 20: (100.5, 0.8, 100.0)}, fund=fund)
    c = sl.candidates(m["BTCUSDT"], "BTCUSDT", T0, T0 + 1000 * BAR, 0.65, 15)
    assert [(x["entry_ts"] - T0) // BAR for x in c] == [12, 21] and (c[1]["exit_ts"] - T0) // BAR == 24
    assert c[0]["funding_events"] == [] and c[1]["funding_events"] == []  # 01:00 = vstup, 02:00 = výstup
    assert c[0]["funding_gaps"] == 0 and c[1]["funding_gaps"] == 0


def test_K8_3_empty_holding_interval_change_and_mixed_intervals():
    stale = sl.prepare({}, {}, {T0 - 10 * 8 * H: 0.01})
    assert sl.funding_completeness(stale, T0, T0) == {"discontinuities": 0, "missing_events": 0, "unknown_coverage": False}
    seq = [(0, 8), (8, 8), (16, 8), (20, 4), (24, 4), (28, 2), (30, 2), (32, 2)]
    f = {T0 + h * H: (0.0001, float(iv)) for h, iv in seq}
    assert sl.funding_completeness(sl.prepare({}, {}, f), T0, T0 + 33 * H)["missing_events"] == 0
    del f[T0 + 30 * H]
    assert sl.funding_completeness(sl.prepare({}, {}, f), T0, T0 + 33 * H)["missing_events"] == 1
    m = {}
    for a, iv in zip(sl.ASSETS, (8, 4, 1)):
        spot, perp = flat()
        m[a] = sl.prepare(spot, perp, {T0 - 8 * H + k * iv * H: (0.001, float(iv)) for k in range(40 // iv + 9)})
    bh = sl.buy_hold(m, START, START, 1)
    assert bh["funding_missing_events"] == 0 and bh["funding_discontinuities"] == 0
    q = sl.START_EQUITY / 3 * (1 - C) / 100
    assert bh["funding"] == pytest.approx(-0.001 * q * 100 * (2 + 5 + 23))  # 8h: 08,16; 4h: 04…20; 1h: 01…23


def test_K8_3_conflicting_duplicate_funding_raises_same_counted():
    audit = {"duplicates_same_value": 0}
    store = {}
    sl.add_row(store, 1, (0.01, 8.0), "BTCUSDT", "fr", audit)
    sl.add_row(store, 1, (0.01, 8.0), "BTCUSDT", "fr", audit)
    assert audit["duplicates_same_value"] == 1
    with pytest.raises(ValueError):
        sl.add_row(store, 1, (0.02, 8.0), "BTCUSDT", "fr", audit)


def _zip_csv(rows):
    import io as _io, zipfile as _zf
    buf = _io.BytesIO()
    with _zf.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "\n".join(",".join(map(str, r)) for r in rows))
    return buf.getvalue()


def _fetcher(conflict=False, missing_month=None):
    import urllib.error
    t = T0

    def f(url):
        if missing_month and missing_month in url and "fundingRate" in url:
            raise urllib.error.HTTPError(url, 404, "nf", None, None)
        if "fundingRate" in url:
            rows = [(t, 8, 0.0001)] + ([(t + 300, 8, 0.0009)] if conflict else [])  # +300 ms ⇒ normalizace na tentýž čas
            return _zip_csv(rows)
        return _zip_csv([(t, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0)])
    return f


def test_K8_3_load_duplicate_conflict_and_missing_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(sl, "ASSETS", ("BTCUSDT",))
    monkeypatch.setattr(sl, "FIRST_MONTH", (2021, 1))
    monkeypatch.setattr(sl, "LAST_MONTH", (2021, 3))
    with pytest.raises(ValueError):
        sl.load(tmp_path / "a", _fetcher(conflict=True))
    _, _, missing, fatal = sl.load(tmp_path / "b", _fetcher(missing_month="2021-02"))
    assert fatal == [{"asset": "BTCUSDT", "kind": "fr", "month": "2021-02"}] and len(missing) == 1


def test_K8_4_unfilled_does_not_set_cooldown_and_notional_uses_equity_at_entry():
    # hold 30 min: nevyplněný vstup v 11 by při cooldownu blokoval do 17; signál 13 (vstup 14) musí projít
    m = market_with({10: (100.5, 0.8, 100.0), 13: (100.5, 0.8, 100.0)}, drop_perp=(11,))
    r, trades, _ = sl.run(m, START, date(2021, 1, 5), 1, 0.65, 30, "t")
    assert [(t["entry_ts"] - T0) // BAR for t in trades] == [14] and r["unfilled_entries"] == 1
    # equity v okamžiku vstupu: ztrátový obchod 3→6 (výstupní open 90) uzavřený před nevyplněným vstupem 41 změní cash
    m2 = market_with({2: (100.5, 0.8, 100.0), 40: (100.5, 0.8, 100.0)}, drop_perp=(41,))
    perp = dict(m2["BTCUSDT"]["perp"])
    perp[T0 + 6 * BAR] = (90.0, 90.0)
    m2["BTCUSDT"] = sl.prepare(m2["BTCUSDT"]["spot"], perp, {})
    trades, _, unfilled = sl.simulate_full(m2, START, date(2021, 1, 5), 0.65, 15, 1)
    assert len(trades) == 1 and len(unfilled) == 1
    assert unfilled[0]["planned_notional"] == pytest.approx(0.1 * (sl.START_EQUITY + trades[0]["net_pnl"]))
    assert trades[0]["net_pnl"] < 0
    again = sl.simulate_full(m2, START, date(2021, 1, 5), 0.65, 15, 1)[2]
    assert [(u["asset"], u["entry_ts"]) for u in again] == [(u["asset"], u["entry_ts"]) for u in unfilled]  # bez duplicit


def test_K8_5_concurrent_run_refused_before_load(tmp_path, monkeypatch):
    calls = _guard(monkeypatch, market=market_with())
    with sl.RunLock(tmp_path):
        with pytest.raises(SystemExit) as e:
            sl.main(["--outdir", str(tmp_path), "--mode", "audit"])
    assert e.value.code == 5 and calls["load"] == 0 and (tmp_path / sl.CONFLICT_LOG).exists()
    sl.main(["--outdir", str(tmp_path), "--mode", "audit"])
    assert calls["load"] == 1


def test_K8_5_atomic_write_keeps_old_content_on_failure(tmp_path, monkeypatch):
    target = tmp_path / "data_audit.json"
    target.write_text("STARÝ")

    def boom(a, b):
        raise OSError("disk")
    monkeypatch.setattr(sl.os, "replace", boom)
    with pytest.raises(OSError):
        sl.atomic_write(target, b"NOVY")
    assert target.read_text() == "STARÝ" and [p.name for p in tmp_path.iterdir()] == ["data_audit.json"]


def test_K8_5_audit_bundle_hashes_and_perf_files_untouched(tmp_path, monkeypatch):
    import json
    (tmp_path / "results.json").write_text("PERF")
    _guard(monkeypatch, market=market_with())
    sl.main(["--outdir", str(tmp_path), "--mode", "audit"])
    d = sl.latest_audit_dir(tmp_path)
    man = json.loads((d / sl.AUDIT_MANIFEST_FILE).read_text())
    assert man["run_id"] == json.loads((d / "data_source.json").read_text())["run_id"]
    assert sl.verify_audit_bundle(d) == (True, []) and (tmp_path / "results.json").read_text() == "PERF"
    (d / "data_source.json").write_text("{}")
    assert sl.verify_audit_bundle(d) == (False, ["data_source.json"])


def test_K8_integration_main_rejected_vs_undecided_and_trades_hash(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(sl, "PERIODS", {"tuning": ("2021-01-02", "2021-01-02"), "validation": ("2021-01-03", "2021-01-04"),
                                        "final_test": ("2021-01-05", "2021-01-06")})
    monkeypatch.setattr(sl, "WF_YEARS", ())
    monkeypatch.setattr(sl, "evaluate", lambda res, bh: tracks(fail=("A1_sharpe_dd", "B2_dd_le_0_6_bh")))
    monkeypatch.setattr(sl, "robustness_checks", lambda dsr, nb, wf: dict(ROBUST_OK))
    monkeypatch.setattr(sl, "safe_dsr", lambda r, n, v: {"dsr": None, "undefined_reason": "mock"})
    monkeypatch.setattr(sl, "latency_info", lambda *a: {"validation": {"x2": {"net_pnl": 1.0}}})
    monkeypatch.setattr(sl, "robustness_context", lambda *a: {"dsr": 0.99, "dsr_defects": {}, "neighbors": {"n": (1.0, {})},
                                                              "wf": {y: (1.0, 5, {}) for y in "abc"}})
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))
    fund = {T0 - 8 * H + k * 8 * H: 0.0001 for k in range(25)}

    def go(market):
        monkeypatch.setattr(sl, "load", lambda cache: (market, [], [], []))
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])
        return json.loads((tmp_path / "results.json").read_text())
    clean = go(market_with(fund=fund))
    assert clean["verdict"] == "ZAMÍTNUTO" and clean["trades_sha256"] == sl.file_sha256(tmp_path / clean["trades_file"])
    bad = go(market_with(fund=fund, drop_perp=(sl.DAY_MS * 2 // BAR + 96,)))
    assert bad["verdict"].startswith("NEROZHODNUTO") and "validation" in bad["verdict_detail"]["benchmark_bad_periods"]


# ---- kolo 9, Q5: zámek spravovaný OS ----
_HOLDER = """
import sys, time
sys.path.insert(0, sys.argv[1])
from research.spot_led import run as sl
with sl.RunLock(sys.argv[2]):
    print("LOCKED", flush=True)
    time.sleep(60)
"""


def _spawn_holder(tmp_path):
    import subprocess, sys as _s
    from pathlib import Path
    root = str(Path(sl.__file__).resolve().parents[2])
    p = subprocess.Popen([_s.executable, "-c", _HOLDER, root, str(tmp_path)], stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "LOCKED"
    return p


def test_K9_5_lock_conflict_logged_and_sigkill_releases(tmp_path, monkeypatch):
    import json, signal
    p = _spawn_holder(tmp_path)
    calls = _guard(monkeypatch, market=market_with())
    with pytest.raises(SystemExit) as e:
        sl.main(["--outdir", str(tmp_path), "--mode", "audit"])
    assert e.value.code == 5 and calls["load"] == 0
    assert json.loads(json.loads((tmp_path / sl.CONFLICT_LOG).read_text().splitlines()[-1])["holder"])["pid"] == p.pid
    p.send_signal(signal.SIGKILL)
    p.wait()
    assert (tmp_path / sl.LOCK_FILE).exists()
    sl.main(["--outdir", str(tmp_path), "--mode", "audit"])  # po násilném ukončení držitele projde
    assert calls["load"] == 1


def test_K9_5_lock_code_has_no_age_based_removal():
    import inspect
    src = inspect.getsource(sl.RunLock)
    assert "unlink" not in src and "st_mtime" not in src and "getmtime" not in src


# ---- kolo 9, Q1/Q3: závislosti kritérií na datech strategie, ztracené signály, globální závady ----
def test_K9_1_strategy_dependency_map_matches_evaluate_by_perturbation():
    from tools.research import decision_gate as dg
    base = {"sharpe": 1.0, "max_drawdown_pct": 10.0, "trades": 15, "profit_factor": 1.5, "net_pnl": 100.0,
            "net_without_top3": 50.0}
    bh = {p: {f"x{m}": {"sharpe": 0.5, "max_drawdown_pct": 20.0} for m in (1, 2, 3)} for p in sl.PERIODS}
    found = {c: set() for c in dg.CRITERIA_DATA}
    for p in sl.PERIODS:
        for alt in ({"sharpe": 5.0, "max_drawdown_pct": 1.0, "trades": 500, "profit_factor": 9.0, "net_pnl": 1e4,
                     "net_without_top3": 1e4},
                    {"sharpe": -5.0, "max_drawdown_pct": 99.0, "trades": 0, "profit_factor": 0.1, "net_pnl": -1e4,
                     "net_without_top3": -1e4}):
            res = {q: {f"x{m}": dict(base) for m in (1, 2, 3)} for q in sl.PERIODS}
            ref = {**sl.evaluate(res, bh)[0], **sl.evaluate(res, bh)[1]}
            res[p] = {f"x{m}": dict(alt) for m in (1, 2, 3)}
            new = {**sl.evaluate(res, bh)[0], **sl.evaluate(res, bh)[1]}
            found.update({c: found[c] | {p} for c in ref if ref[c] != new[c]})
    assert {c: tuple(sorted(x)) for c, x in found.items()} == \
        {c: tuple(sorted(d["strategy"])) for c, d in dg.CRITERIA_DATA.items()}


def test_K9_1_missing_bar_silently_removing_signals_is_counted():
    clean = sl.run(market_with(), date(2021, 1, 2), date(2021, 1, 3), 1, 0.65, 15, "t")[0]
    assert clean["signal_bars_lost_to_gaps"] == 0
    r = sl.run(market_with(drop_perp=(400,)), date(2021, 1, 2), date(2021, 1, 3), 1, 0.65, 15, "t")[0]
    assert r["signal_bars_lost_to_gaps"] == 6 and sl.strategy_defects(r) == {"signal_bars_lost_to_gaps": 6}


def test_K9_1_tuning_gap_is_global(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(sl, "PERIODS", {"tuning": ("2021-01-02", "2021-01-02"), "validation": ("2021-01-03", "2021-01-04"),
                                        "final_test": ("2021-01-05", "2021-01-06")})
    monkeypatch.setattr(sl, "WF_YEARS", ())
    monkeypatch.setattr(sl, "evaluate", lambda res, bh: tracks(fail=("A2_trades_ge_30", "B3_final_x2_profit")))
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))
    fund = {T0 - 8 * H + k * 8 * H: 0.0001 for k in range(25)}
    for drop, expect in (((), "ZAMÍTNUTO"), ((300,), "NEROZHODNUTO — globální")):  # bar 300 = 2. 1. 01:00 (ladění)
        monkeypatch.setattr(sl, "load", lambda cache: (market_with(fund=fund, drop_perp=drop), [], [], []))
        sl.main(["--outdir", str(tmp_path), "--mode", "perf"])
        assert json.loads((tmp_path / "results.json").read_text())["verdict"].startswith(expect)


# ---- kolo 9, bod 6: NEZÁVISLÝ ekonomický přepočet ----
# Literály z ručního přepočtu v Decimal (calc/indep_sl.py, bez importu runneru). Předem stanovená přesnost 1e-6 USDT.
TOL = 1e-6


def _econ_market():
    m = {}
    fund = {T0 + k * H: (0.0, 1.0) for k in range(-3, 41)}
    fund[T0 + H] = (0.001, 1.0)
    fund[T0 + 24 * H] = (0.0005, 1.0)
    for a in sl.ASSETS:
        spot, perp = flat()
        if a == "BTCUSDT":
            spot[T0 + 10 * BAR] = (100.5, 10.0, 8.0)   # long signál
            spot[T0 + 30 * BAR] = (99.5, 10.0, 2.0)    # short signál
            spot[T0 + 284 * BAR] = (100.5, 10.0, 8.0)  # long přes půlnoc
            perp[T0 + 12 * BAR] = (100.4, 100.0)       # open v 01:00 = cena pro funding
            perp[T0 + 17 * BAR] = (101.0, 101.0)       # výstup 1
            perp[T0 + 37 * BAR] = (99.0, 99.0)         # výstup 2
            perp[T0 + 287 * BAR] = (100.0, 102.0)      # close 23:55 = ocenění přes půlnoc
            perp[T0 + 288 * BAR] = (102.5, 102.5)      # open 00:00 = cena pro funding
            perp[T0 + 291 * BAR] = (103.0, 103.0)      # výstup 3
        m[a] = sl.prepare(spot, perp, fund)
    return m


def test_K9_6_independent_trade_accounting_sizing_mtm_and_equity():
    trades, curve = sl.simulate(_econ_market(), START, date(2021, 1, 2), 0.65, 30, 1)
    assert [(t["side"], (t["entry_ts"] - T0) // BAR, (t["exit_ts"] - T0) // BAR) for t in trades] == \
        [(1, 11, 17), (-1, 31, 37), (1, 285, 291)]
    for t, (q, n) in zip(trades, ((10.0, 6.6845), (10.0066845, 7.7166547522), (10.0144011548, 27.1921034555))):
        assert abs(t["qty"] - q) <= TOL and abs(t["net_pnl"] - n) <= TOL, (t["qty"], t["net_pnl"])
    assert abs(curve[date(2021, 1, 1)] - 10033.2783009289) <= TOL   # 2 realizované + MTM přes půlnoc
    assert abs(curve[date(2021, 1, 2)] - 10041.5932582077) <= TOL   # equity po uzavření všech


def test_K9_6_independent_benchmark_accounting():
    bh = sl.buy_hold(_econ_market(), START, START, 1)
    assert abs(bh["funding"] - (-10.001818)) <= 1e-4 and abs(bh["net_pnl"] - 33.5248285) <= 1e-4  # runner: 4 místa


def test_K9_2_ops_fingerprint_protocol_or_workflow_change_invalidates(tmp_path):
    import json
    (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision()))
    assert sl.semantics_gate(tmp_path) == (True, "ok")
    for k in sl.OPS_SOURCES:
        (tmp_path / sl.SEMANTICS_FILE).write_text(json.dumps(valid_decision(ops_sha256={**sl.ops_fingerprint(), k: "0" * 64})))
        ok, why = sl.semantics_gate(tmp_path)
        assert ok is False and "ops_sha256" in why
