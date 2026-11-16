"""Syntetické testy K9 krok 0 (audit) a fáze A (agregace, brána). Žádná tržní data, žádné výnosy."""
import hashlib
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from research.k9_round_number import audit, phase_a


def _zip_month(tmp_path, y, m, minutes=None, header=False, micro=False, drop=0):
    lo = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
    n = pd.Timestamp(lo + pd.offsets.MonthBegin(1)).value // 60_000_000_000 - lo.value // 60_000_000_000
    idx = pd.date_range(lo, periods=n if minutes is None else minutes, freq="1min")[drop:]
    ms = idx.as_unit("ns").asi8 // (1_000 if micro else 1_000_000)
    buf = io.StringIO()
    if header:
        buf.write(",".join(audit.KLINE_COLS) + "\n")
    for t in ms:
        buf.write(f"{t},1,2,0.5,1.5,10,{t+59999},15,3,5,7,0\n")
    zp = tmp_path / f"X-1m-{y}-{m:02d}.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr(zp.name.replace(".zip", ".csv"), buf.getvalue())
    cp = tmp_path / (zp.name + ".CHECKSUM")
    cp.write_text(hashlib.sha256(zp.read_bytes()).hexdigest() + "  " + zp.name + "\n")
    return zp, cp


def test_audit_ok_full_month_with_and_without_header(tmp_path):
    for hdr in (False, True):
        zp, cp = _zip_month(tmp_path, 2021, 2, header=hdr)
        r = audit.audit_month("BTCUSDT", 2021, 2, zp, cp)
        assert r.status == "OK" and r.present_minutes == 28 * 1440 and r.coverage == 1.0


def test_audit_microsecond_timestamps(tmp_path):
    zp, cp = _zip_month(tmp_path, 2025, 2, micro=True)
    assert audit.audit_month("BTCUSDT", 2025, 2, zp, cp).status == "OK"


def test_audit_checksum_mismatch_before_parse(tmp_path):
    zp, cp = _zip_month(tmp_path, 2021, 2)
    cp.write_text("0" * 64 + "  x.zip")
    assert audit.audit_month("BTCUSDT", 2021, 2, zp, cp).status == "CHECKSUM_FAIL"
    cp.write_text("garbage")
    assert audit.audit_month("BTCUSDT", 2021, 2, zp, cp).status == "CHECKSUM_FAIL"


def test_audit_low_coverage_and_missing(tmp_path):
    zp, cp = _zip_month(tmp_path, 2021, 2, drop=int(28 * 1440 * 0.02))
    r = audit.audit_month("BTCUSDT", 2021, 2, zp, cp)
    assert r.status == "LOW_COVERAGE" and r.coverage < 0.99
    assert audit.audit_month("BTCUSDT", 2021, 3, None, None).status == "MISSING"


def test_audit_corrupt_zip_is_parse_fail(tmp_path):
    zp = tmp_path / "bad.zip"
    zp.write_bytes(b"not a zip")
    cp = tmp_path / "bad.zip.CHECKSUM"
    cp.write_text(hashlib.sha256(b"not a zip").hexdigest() + "  bad.zip")
    assert audit.audit_month("BTCUSDT", 2021, 2, zp, cp).status == "PARSE_FAIL"


def test_gate_threshold_90_percent():
    mk = lambda st: audit.MonthAudit("BTCUSDT", "2021-01", "u", st)
    assert audit.gate([mk("OK")] * 9 + [mk("MISSING")])["verdict"] == "DATA GO"
    g = audit.gate([mk("OK")] * 8 + [mk("MISSING")] * 2)
    assert g["verdict"] == "DATA NO-GO" and len(g["excluded"]) == 2
    assert audit.gate([])["verdict"] == "DATA NO-GO"


def test_months_range_count():
    assert len(list(audit.months())) == 6 * 12 + 10


def _events(days, vals, start="2021-01-01"):
    t = pd.Timestamp(start, tz="UTC") + pd.to_timedelta(days, unit="D")
    return pd.DataFrame({"time": t, "r_vol": vals, "m2": vals})


def test_pooled_diff_point_is_weighted_by_round_counts():
    a = {"round": _events([0, 1, 2], [1.0, 1.0, 1.0]), "placebo": _events([0, 1], [0.0, 0.0])}
    b = {"round": _events([0], [0.5]), "placebo": _events([0], [0.5])}
    res = phase_a.pooled_diff({"A": a, "B": b}, "r_vol", reps=200)
    assert res["d"] == pytest.approx(0.75 * 1.0 + 0.25 * 0.0)
    assert res["per_asset"]["A"]["d"] == 1.0 and res["n_round"] == 4


def test_pooled_diff_null_ci_covers_zero_and_effect_excludes_zero():
    rng = np.random.default_rng(1)
    days = np.repeat(np.arange(200), 3)
    null = {"round": _events(days, rng.normal(0, 1, len(days))),
            "placebo": _events(days, rng.normal(0, 1, len(days)))}
    r0 = phase_a.pooled_diff({"A": null}, "r_vol", reps=2000)
    assert r0["lo"] < 0 < r0["hi"]
    eff = {"round": _events(days, rng.normal(0.3, 1, len(days))),
           "placebo": _events(days, rng.normal(0, 1, len(days)))}
    r1 = phase_a.pooled_diff({"A": eff}, "r_vol", reps=2000)
    assert r1["lo"] > 0


def test_pooled_diff_drops_nan_metric_rows():
    a = {"round": _events([0, 1], [1.0, np.nan]), "placebo": _events([0, 1], [0.0, 0.0])}
    res = phase_a.pooled_diff({"A": a}, "m2", reps=100)
    assert res["d"] == 1.0 and res["n_round"] == 1 and np.isfinite(res["lo"])


def test_gap_in_minutes_never_creates_event():
    idx = pd.date_range("2021-01-01", periods=200, freq="1min", tz="UTC")
    df = pd.DataFrame({"high": 990.0, "low": 980.0, "close": 985.0, "volume": 10.0, "taker_buy": 5.0}, index=idx)
    df.iloc[150, df.columns.get_loc("high")] = 1001.0
    gappy = df.drop(df.index[100:130])  # 30min mezera v okně posledních 60 minut
    ev = phase_a.asset_events(gappy, 1000.0)
    assert ev["round"].empty
    ev_full = phase_a.asset_events(df, 1000.0)
    assert len(ev_full["round"]) == 1


def test_split_period_boundary():
    ev = pd.DataFrame({"time": pd.to_datetime(["2023-12-31 23:59", "2024-01-01 00:00"], utc=True),
                       "r_vol": [1, 2], "m2": [0, 0]})
    assert list(phase_a.split_period(ev, "dev")["r_vol"]) == [1]
    assert list(phase_a.split_period(ev, "final")["r_vol"]) == [2]


def test_evaluate_gate_rules():
    ok1 = {"d": 0.12, "lo": 0.02}
    ok2 = {"d": 0.01, "lo": 0.001}
    fin = {"d": 0.05, "lo": 0.01}
    assert phase_a.evaluate(ok1, ok2, fin)["verdict"].startswith("GO")
    assert phase_a.evaluate({"d": 0.09, "lo": 0.02}, ok2, fin, 0.9)["verdict"] == "METHOD NO-GO"
    assert phase_a.evaluate(ok1, {"d": 0.01, "lo": -0.001}, fin, 0.9)["verdict"] == "METHOD NO-GO"
    assert phase_a.evaluate(ok1, ok2, {"d": 0.05, "lo": -0.01}, 0.9)["verdict"] == "METHOD NO-GO"


# --- dodatek 1 (dialog 0353): neplatné repliky, síla, expozice, CI po aktivech ---

def test_evaluate_invalid_reps_over_5pct_is_inconclusive_even_if_gate_passes():
    ok1, ok2, fin = {"d": 0.2, "lo": 0.05}, {"d": 0.02, "lo": 0.001}, {"d": 0.1, "lo": 0.01}
    bad = dict(ok1, invalid_frac=0.051)
    assert phase_a.evaluate(bad, ok2, fin, 0.95)["verdict"] == "INCONCLUSIVE (neplatné repliky)"
    assert phase_a.evaluate(dict(ok1, invalid_frac=0.05), ok2, fin, 0.95)["verdict"].startswith("GO")


def test_evaluate_low_power_failure_is_inconclusive_not_no_go():
    ok2, fin = {"d": 0.02, "lo": 0.001}, {"d": 0.1, "lo": 0.01}
    fail = {"d": 0.05, "lo": -0.02}
    assert phase_a.evaluate(fail, ok2, fin, 0.5)["verdict"] == "INCONCLUSIVE (nízká síla)"
    assert phase_a.evaluate(fail, ok2, fin, None)["verdict"] == "INCONCLUSIVE (nízká síla)"
    assert phase_a.evaluate(fail, ok2, fin, 0.8)["verdict"] == "METHOD NO-GO"


def test_power_table_monotone_in_days_and_uses_only_counts():
    few = phase_a.power_table(np.full(30, 2), np.full(30, 4), effects=(0.20,), sds=(1.0,), rhos=(0.3,),
                              sims=60, reps=300)
    many = phase_a.power_table(np.full(1000, 2), np.full(1000, 4), effects=(0.20,), sds=(1.0,), rhos=(0.3,),
                               sims=60, reps=300)
    assert few["power"].iloc[0] < 0.5 < many["power"].iloc[0]
    assert phase_a.decisive_power(many) == many["power"].iloc[0]
    zero = phase_a.power_table(np.full(500, 2), np.full(500, 4), effects=(0.0,), sds=(1.0,), rhos=(0.3,),
                               sims=60, reps=300)
    assert zero["power"].iloc[0] <= 0.05


def test_exposure_table_counts_by_asset_year_hour():
    t = pd.to_datetime(["2021-01-01 03:10", "2021-01-01 03:50", "2022-05-01 12:00"], utc=True)
    ev = pd.DataFrame({"time": t, "level": [100.0, 200.0, 300.0], "direction": [1, 1, -1],
                       "r_vol": 0.0, "m2": 0.0})
    tab = phase_a.exposure_table({"X": {"round": ev, "placebo": ev.iloc[:1]}})
    r = tab[(tab.kind == "round") & (tab.year == 2021) & (tab.hour == 3)]
    assert int(r["n"].iloc[0]) == 2 and float(r["mean_level"].iloc[0]) == 150.0
    assert int(tab[tab.kind == "placebo"]["n"].sum()) == 1


def test_pooled_diff_reports_per_asset_ci_and_invalid_frac():
    rng = np.random.default_rng(1)
    days = pd.date_range("2021-01-01", periods=200, freq="D", tz="UTC")
    def ev(shift):
        return pd.DataFrame({"time": days + pd.Timedelta(hours=1), "level": 1.0, "direction": 1,
                             "r_vol": rng.normal(shift, 0.1, len(days)), "m2": 0.0})
    res = phase_a.pooled_diff({"A": {"round": ev(0.5), "placebo": ev(0.0)},
                               "B": {"round": ev(0.0), "placebo": ev(0.0)}}, "r_vol", reps=500)
    assert res["invalid_frac"] == 0.0 and res["reps"] == 500
    a, b = res["per_asset"]["A"], res["per_asset"]["B"]
    assert a["lo"] > 0.4 and b["lo"] < 0 < b["hi"]


def test_step0_runner_offline_writes_manifest_and_deletes_zips(tmp_path, monkeypatch):
    """Runner kroku 0 bez sítě: 1 OK měsíc, ostatní MISSING ⇒ DATA NO-GO, manifest se SHA, ZIP smazán."""
    import json

    from research.k9_round_number import step0

    ok_zip, ok_ck = _zip_month(tmp_path, 2020, 1)

    def fake_download(sym, y, m, dest):
        if (sym, y, m) == ("BTCUSDT", 2020, 1):
            dest.mkdir(parents=True, exist_ok=True)
            z, c = dest / ok_zip.name, dest / ok_ck.name
            z.write_bytes(ok_zip.read_bytes())
            c.write_text(ok_ck.read_text())
            return z, c
        return None, None

    monkeypatch.setattr(audit, "download_month", fake_download)
    g = step0.run(tmp_path / "out", tmp_path / "data")
    man = json.loads((tmp_path / "out" / "step0_manifest.json").read_text())
    assert g["verdict"] == "DATA NO-GO" and g["ok_months"] == 1 and g["total_months"] == 3 * 82
    ok = [r for r in man["months"] if r["status"] == "OK"]
    assert len(ok) == 1 and len(ok[0]["sha256"]) == 64
    assert not (tmp_path / "data" / "BTCUSDT" / ok_zip.name).exists()


def _price_zip(tmp_path, sym, y, m, base, amp):
    """Syntetický měsíc s oscilací kolem kulaté úrovně (dotyky existují), objem konstantní."""
    lo = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
    n = int((lo + pd.offsets.MonthBegin(1) - lo) / pd.Timedelta("1min"))
    idx = pd.date_range(lo, periods=n, freq="1min")
    rng = np.random.default_rng(y * 100 + m)
    c = base + amp * np.sin(np.arange(n) / 300.0) + rng.normal(0, amp * 0.01, n)
    ms = idx.as_unit("ns").asi8 // 1_000_000
    buf = io.StringIO()
    for t, x in zip(ms, c):
        buf.write(f"{t},{x},{x*1.0002},{x*0.9998},{x},10,{t+59999},15,3,{rng.uniform(3, 7):.3f},7,0\n")
    d = tmp_path / "src" / sym
    d.mkdir(parents=True, exist_ok=True)
    zp = d / f"{sym}-1m-{y}-{m:02d}.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr(zp.name.replace(".zip", ".csv"), buf.getvalue())
    return zp


def test_phase_a_runner_offline_sha_guard_and_outputs(tmp_path, monkeypatch):
    import json
    import shutil

    from research.k9_round_number import phase_a_run

    months_ = [(2023, 12), (2024, 1)]
    src = {(s, y, m): _price_zip(tmp_path, s, y, m, b, a)
           for s, b, a in (("BTCUSDT", 30000, 1500), ("XRPUSDT", 0.5, 0.15)) for y, m in months_}
    recs = [{"symbol": s, "month": f"{y}-{m:02d}", "status": "OK",
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for (s, y, m), p in src.items()]
    recs.append({"symbol": "ETHUSDT", "month": "2023-12", "status": "LOW_COVERAGE", "sha256": ""})
    man = tmp_path / "step0_manifest.json"
    man.write_text(json.dumps({"gate": {"verdict": "DATA GO"}, "months": recs}))

    def fetch(sym, y, m, dest):
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / src[(sym, y, m)].name
        shutil.copy(src[(sym, y, m)], out)
        return out, None

    res = phase_a_run.run(man, tmp_path / "out", tmp_path / "data", reps=50, fetch=fetch)
    out = json.loads((tmp_path / "out" / "phaseA_results.json").read_text())
    assert out["gate"]["verdict"] in {"GO (jen fáze B dodatek)", "METHOD NO-GO", "INCONCLUSIVE (nízká síla)",
                                      "INCONCLUSIVE (neplatné repliky)"}
    ev = pd.read_csv(tmp_path / "out" / "phaseA_events.csv.gz")
    assert set(ev["asset"]) <= {"BTCUSDT", "XRPUSDT"} and len(ev) == len(res["events"]) > 0
    # nezávislý přepočet bodového D1 z jednotlivých událostí (dev období) = výstup runneru
    dev = ev[pd.to_datetime(ev["time"], utc=True) < pd.Timestamp("2024-01-01", tz="UTC")]
    w = dev[dev.kind == "round"].groupby("asset").size()
    diff = {a: g[g.kind == "round"].r_vol.mean() - g[g.kind == "placebo"].r_vol.mean() for a, g in dev.groupby("asset")}
    assert abs(sum(diff[a] * w[a] for a in w.index) / w.sum() - out["dev"]["D1"]["d"]) < 1e-9

    # SHA neshoda ⇒ konec s chybou, fáze A se nespočte
    recs[0]["sha256"] = "0" * 64
    man.write_text(json.dumps({"gate": {"verdict": "DATA GO"}, "months": recs}))
    with pytest.raises(RuntimeError, match="SHA-256"):
        phase_a_run.run(man, tmp_path / "out2", tmp_path / "data", reps=50, fetch=fetch)
    # krok 0 bez DATA GO ⇒ nespouští se
    man.write_text(json.dumps({"gate": {"verdict": "DATA NO-GO"}, "months": recs}))
    with pytest.raises(RuntimeError, match="DATA GO"):
        phase_a_run.run(man, tmp_path / "out3", tmp_path / "data", reps=50, fetch=fetch)
