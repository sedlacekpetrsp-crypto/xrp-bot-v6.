"""Syntetické testy K9 fáze B (dodatek 2 + oprava 1). Žádná tržní data, žádný výnos K9."""
import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from research.k9_round_number import phase_b, phase_b_run, verify_phase_b
from research.k9_round_number.audit import DEV_END


def _grid(start, n, price=100.0, step_fn=None):
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    o = np.full(n, price, float)
    if step_fn is not None:
        o = np.array([step_fn(i) for i in range(n)], float)
    c = np.roll(o, -1)
    c[-1] = o[-1]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c), "low": np.minimum(o, c), "close": c,
                         "volume": 10.0, "taker_buy": 5.0}, index=idx)


def _ev(times, direction=1, level=100.0):
    return pd.DataFrame({"time": pd.to_datetime(times, utc=True), "level": level, "direction": direction})


# ------------------------------------------------------------ mechanika obchodu
def test_entry_next_open_exit_close_t_plus_h_and_sign():
    g = _grid("2022-03-01 00:00", 200, step_fn=lambda i: 100 + i)  # open_i = 100+i, close_i = 101+i
    tr, st = phase_b.build_trades(g, _ev(["2022-03-01 01:00"]), 15)
    r = tr.iloc[0]
    assert r.entry == 100 + 61 and r.exit == 101 + 75  # open t+1, close t+H
    assert r.gross == pytest.approx(176 / 161 - 1)
    tr2, _ = phase_b.build_trades(g, _ev(["2022-03-01 01:00"], direction=-1), 15)
    assert tr2.iloc[0].gross == pytest.approx(-(176 / 161 - 1))
    assert r.net_x2 == pytest.approx(r.gross - 2 * phase_b.COST_RT)


def test_no_lookahead_minute_t_close_does_not_enter():
    g = _grid("2022-03-01 00:00", 200, step_fn=lambda i: 100 + i)
    base = phase_b.build_trades(g, _ev(["2022-03-01 01:00"]), 15)[0].iloc[0].gross
    g2 = g.copy()
    g2.iloc[60, g2.columns.get_loc("close")] = 1e6  # extrém v signální minutě t
    assert phase_b.build_trades(g2, _ev(["2022-03-01 01:00"]), 15)[0].iloc[0].gross == base


def test_one_position_per_asset_blocks_until_t_plus_h_plus_1():
    g = _grid("2022-03-01 00:00", 300)
    times = ["2022-03-01 01:00", "2022-03-01 01:15", "2022-03-01 01:16"]
    tr, st = phase_b.build_trades(g, _ev(times), 15)
    assert list(tr["time"].dt.strftime("%H:%M")) == ["01:00", "01:16"] and st["blocked"] == 1


def test_missing_minute_invalidates_but_still_blocks():
    g = _grid("2022-03-01 00:00", 300)
    g.iloc[65, :] = np.nan  # minuta uvnitř okna 1. obchodu
    tr, st = phase_b.build_trades(g, _ev(["2022-03-01 01:00", "2022-03-01 01:10", "2022-03-01 01:30"]), 15)
    assert list(tr["time"].dt.strftime("%H:%M")) == ["01:30"]
    assert len(st["invalid"]) == 1 and st["blocked"] == 1
    assert phase_b.missing_frac({"X": {"round": st}}, "dev") == pytest.approx(0.5)


def test_window_past_end_is_invalid():
    g = _grid("2022-03-01 00:00", 70)
    tr, st = phase_b.build_trades(g, _ev(["2022-03-01 01:00"]), 15)
    assert tr.empty and len(st["invalid"]) == 1


@pytest.mark.parametrize("t,H,n", [("07:44", 15, 0), ("07:45", 15, 1), ("07:59", 60, 1), ("08:00", 15, 0),
                                   ("23:30", 60, 1), ("06:59", 60, 0), ("07:00", 60, 1)])
def test_funding_crossings_entry_inclusive_end_exclusive(t, H, n):
    # vstup = t+1; konec = konec minuty t+H. „07:59“ ⇒ vstup 08:00 přesně ⇒ počítá se (konzervativně).
    g = _grid("2022-03-01 00:00", 2000)
    tr, _ = phase_b.build_trades(g, _ev([f"2022-03-01 {t}"]), H)
    assert tr.iloc[0].funding_crossings == n
    assert tr.iloc[0].net_x3 == pytest.approx(tr.iloc[0].gross - 3 * (phase_b.COST_RT + 0.0003 * n))


# ------------------------------------------------------------ výběr H a předbrána
def _dev(h15_gross, h60_gross, n=10):
    def tr(gr, H):
        return pd.DataFrame({"kind": "round", "gross": [gr] * n, "net_x1": [gr - phase_b.COST_RT] * n, "H": H})
    return {15: tr(h15_gross, 15), 60: tr(h60_gross, 60)}


def test_pregate_blocks_final_when_gross_below_three_x_cost():
    sel = phase_b.dev_selection(_dev(0.0041, 0.0030), {15: 0, 60: 0})
    assert sel["final_open"] is False and sel["h_star"] is None and sel["verdict"].startswith("NO-GO")


def test_pregate_pass_selects_best_net_and_tie_shorter():
    assert phase_b.dev_selection(_dev(0.0042, 0.0050), {15: 0, 60: 0})["h_star"] == 60
    assert phase_b.dev_selection(_dev(0.0050, 0.0050), {15: 0, 60: 0})["h_star"] == 15


def test_missing_over_one_percent_is_inconclusive_in_dev():
    sel = phase_b.dev_selection(_dev(0.01, 0.01), {15: 0.02, 60: 0})
    assert sel["final_open"] is False and sel["verdict"].startswith("INCONCLUSIVE")


# ------------------------------------------------------------ brány závěru
def _trades(mu, n_days=300, per_day=4, seed=1, kind="round", sd=0.004):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2024-01-02 03:00", periods=n_days, freq="D", tz="UTC").repeat(per_day)
    t = t + pd.to_timedelta(np.tile(np.arange(per_day) * 97, n_days), unit="min")
    g = rng.normal(mu, sd, len(t))
    assets = np.tile(["BTCUSDT", "ETHUSDT", "XRPUSDT"], len(t) // 3 + 1)[: len(t)]
    df = pd.DataFrame({"asset": assets, "kind": kind, "time": t, "entry_time": t + pd.Timedelta(minutes=1),
                       "direction": 1, "H": 15, "gross": g, "funding_crossings": 0})
    for m in (1, 2, 3):
        df[f"net_x{m}"] = g - m * phase_b.COST_RT
    return df


def _rand(rnd, mu, seed=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"asset": rnd["asset"].repeat(5).values, "time": rnd["time"].repeat(5).values,
                         "src_time": rnd["time"].repeat(5).values, "gross": rng.normal(mu, 0.004, 5 * len(rnd))})


def test_planted_edge_go_and_controls_no_go():
    rnd = _trades(0.006, n_days=800)  # 2024-01 .. 2026-03 ⇒ 3 kalendářní roky závěru
    plc = _trades(0.0, n_days=800, seed=2, kind="placebo")
    pnl = phase_b.daily_pnl(rnd, DEV_END, pd.Timestamp("2026-03-12", tz="UTC"))
    ok = phase_b.evaluate_final(rnd, plc, _rand(rnd, 0.0), pnl, 0.99, 0.0, reps=500)
    assert ok["verdict"].startswith("GO") and all(ok["gates"].values())
    # placebo stejně dobré ⇒ c) selže ⇒ NO-GO
    same = phase_b.evaluate_final(rnd, _trades(0.006, n_days=800, seed=2, kind="placebo"), _rand(rnd, 0.0), pnl, 0.99, 0.0, reps=500)
    assert same["verdict"] == "NO-GO" and not same["gates"]["c"]
    # náhodný vstup stejně dobrý ⇒ d) selže ⇒ NO-GO
    assert phase_b.evaluate_final(rnd, plc, _rand(rnd, 0.006), pnl, 0.99, 0.0, reps=500)["verdict"] == "NO-GO"
    # nízká / chybějící síla ⇒ INCONCLUSIVE, chybějící minuty > 1 % ⇒ INCONCLUSIVE
    assert phase_b.evaluate_final(rnd, plc, _rand(rnd, 0.0), pnl, 0.5, 0.0, reps=200)["verdict"].startswith("INCONCLUSIVE")
    assert phase_b.evaluate_final(rnd, plc, _rand(rnd, 0.0), pnl, None, 0.0, reps=200)["verdict"].startswith("INCONCLUSIVE")
    assert "chybějící" in phase_b.evaluate_final(rnd, plc, _rand(rnd, 0.0), pnl, 0.99, 0.02, reps=200)["verdict"]


def test_zero_edge_is_no_go_and_net_below_cost():
    rnd = _trades(0.0)
    pnl = phase_b.daily_pnl(rnd, DEV_END, pd.Timestamp("2024-12-31", tz="UTC"))
    r = phase_b.evaluate_final(rnd, _trades(0.0, seed=2, kind="placebo"), _rand(rnd, 0.0), pnl, 0.99, 0.0, reps=300)
    assert r["verdict"] == "NO-GO" and not r["gates"]["a"] and not r["gates"]["e"]


def test_stability_requires_two_assets_and_two_years():
    rnd = _trades(0.006, n_days=900)
    rnd.loc[rnd["asset"] != "BTCUSDT", ["net_x1"]] = -0.01
    st = phase_b.stability(rnd)
    assert st["assets_pos"] == 1 and not st["ok"]


def test_bootstrap_same_days_identical_series_zero_diff():
    a = _trades(0.003)
    r = phase_b.boot(a, "gross", a.copy(), "gross", reps=300, b_time_col="time")
    assert r["point"] == 0 and r["lo"] == pytest.approx(0) and r["hi"] == pytest.approx(0) and r["invalid_frac"] == 0


def test_random_trades_same_hour_day_excluding_signal_minute():
    g = _grid("2024-02-01 00:00", 3000, step_fn=lambda i: 100 + 0.01 * i)
    src = pd.DataFrame({"asset": ["XRPUSDT"], "time": [pd.Timestamp("2024-02-01 13:20", tz="UTC")], "direction": [1]})
    r = phase_b.random_trades(g, src, 15, np.random.default_rng(0))
    assert len(r) == 5 and (r["time"].dt.hour == 13).all() and (r["time"].dt.day == 1).all()
    assert not (r["time"] == src["time"].iloc[0]).any()


def test_drawdown_and_daily_pnl_zero_days():
    s = pd.Series([1.0, -2.0, 0.5, 3.0])
    assert phase_b.max_drawdown(s) == pytest.approx(2.0)
    p = phase_b.daily_pnl(_trades(0.0, n_days=3, per_day=1), DEV_END, pd.Timestamp("2024-01-10", tz="UTC"))
    assert len(p) == 10 and (p == 0).sum() == 7


# ------------------------------------------------------------ runner: fail closed
def test_owner_approval_line_required():
    with pytest.raises(phase_b_run.NotApproved):
        phase_b_run.check_approval("výkon jen s „SCHVÁLENO: výkonnost K9“ (citace v textu)\n")
    with pytest.raises(phase_b_run.NotApproved):
        phase_b_run.check_approval("2026-11-12 SCHVÁLENO: výkonnost K7\n")
    phase_b_run.check_approval("x\n2026-11-20 SCHVÁLENO: výkonnost K9 — jediný běh\n")


def test_stage_final_refuses_without_open_selection():
    with pytest.raises(RuntimeError):
        phase_b_run.stage_final({}, {"final_open": False, "verdict": "NO-GO"}, {})
    with pytest.raises(RuntimeError):
        phase_b_run.stage_final({}, {"final_open": True, "h_star": 30}, {})


def _btc_frame(start, n, seed):
    rng = np.random.default_rng(seed)
    o = 10000 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    c = np.roll(o, -1)
    c[-1] = o[-1]
    hi = np.maximum(o, c) * 1.0005
    lo = np.minimum(o, c) * 0.9995
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": 10.0, "taker_buy": 5.0}, index=idx)


def test_stage_dev_never_reads_final_period():
    n = 6 * 1440
    df = _btc_frame(DEV_END - pd.Timedelta(minutes=n // 2), n, 7)
    sel1, tr1 = phase_b_run.stage_dev({"BTCUSDT": df}, "sha")
    df2 = df.copy()
    df2.loc[df2.index >= DEV_END, ["open", "high", "low", "close"]] *= 3.0  # „otrava“ závěru
    sel2, tr2 = phase_b_run.stage_dev({"BTCUSDT": df2}, "sha")
    assert sel1["per_h"] == sel2["per_h"] and len(tr1) == len(tr2)
    assert (pd.to_datetime(tr1["time"], utc=True) < DEV_END).all()
    assert (pd.to_datetime(tr1["exit_time"], utc=True) < DEV_END).all()


def test_end_to_end_final_and_independent_recompute():
    n = 8 * 1440
    df = _btc_frame(DEV_END, n, 11)
    sel = {"final_open": True, "h_star": 15}
    pt = {"H15_final_round": {phase_b.POWER_KEY[15]: 0.99}}
    res, tr = phase_b_run.stage_final({"BTCUSDT": df, "ETHUSDT": df / 10}, sel, pt, reps=200)
    assert res["n_round"] > 0 and res["n_placebo"] > 0 and res["n_random"] > 0
    assert res["dsr"]["n_trials"] == phase_b.DSR_N == 225
    rec = verify_phase_b.recompute(tr, "2024-01-01", str(df.index.max()), phase_b.DSR_N)
    assert verify_phase_b.compare(rec, json.loads(json.dumps(res, default=str))) == []
    bd = phase_b.breakdown(tr[tr["kind"] == "round"])
    assert bd["n"].sum() == res["n_round"]
