"""A4 VORTEX+CHOP 5/15m BTC — diagnostika dle PROTOCOL.md (`0c506a1`).
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.vortex_chop.run --cache /tmp/vision-a4 --outdir research/vortex_chop
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

SPOT = "https://data.binance.vision/data/spot/monthly/klines"
PERP = "https://data.binance.vision/data/futures/um/monthly/klines"
SYMBOL = "BTCUSDT"
START, END = (2020, 1), (2026, 10)
TFS = ("5m", "15m")
GRID = [(n, th) for n in (14, 28) for th in (38.2, 50.0)]
PERIODS = {"tuning": ("2020-01-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
COST_STEP = 0.01            # stopa P: q = 0,50 + k*0,01
PERP_COST = 0.00095 + 0.0002  # stopa F: round-trip fee + skluz (×1)
MULTS = (1, 2, 3)
NOTIONAL = 10_000.0
MIN_SIGNALS = 1000
DSR_N, DSR_VAR_ANNUAL = 210, 0.5
TINY_MOVE = 0.0002


def cell_name(tf, n, th):
    return f"{tf}_n{n}_chop{th:g}"


# ------------------------------------------------------------------ data
def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 451):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


def months():
    y, m = START
    while (y, m) <= END:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


def parse_klines(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    out = []
    for r in csv.reader(io.StringIO(text)):
        if r and r[0].strip().isdigit():
            out.append((_ms(int(r[0])), float(r[1]), float(r[2]), float(r[3]), float(r[4])))
    return out


def get_verified(url, cache, fetcher=fetch):
    p = Path(cache) / url.split("binance.vision/", 1)[1]
    if p.exists():
        payload = p.read_bytes()
    else:
        payload = fetcher(url)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    expected = fetcher(url + ".CHECKSUM").decode().split()[0].lower()
    if expected != sha:
        raise RuntimeError(f"SHA-256 MISMATCH {url}")
    return payload, sha


def load_series(base, tf, cache, manifest, fetcher=fetch):
    bars = {}
    for y, m in months():
        url = f"{base}/{SYMBOL}/{tf}/{SYMBOL}-{tf}-{y}-{m:02d}.zip"
        payload, sha = get_verified(url, cache, fetcher)
        manifest.append({"url": url, "sha256": sha, "checksum": "ok"})
        for b in parse_klines(payload):
            bars[b[0]] = b
    return [bars[k] for k in sorted(bars)]


# ------------------------------------------------------------------ indikátory
def signals(bars, n, th):
    """bars: [(t, o, h, l, c)]. Vrací {index_t: +1/-1} pro signál po uzavření baru t (předpověď t+1).
    Jen data ≤ t. Mezery v datech: okno přes mezeru se nepočítá (kontinuita kroku)."""
    out = {}
    if len(bars) < n + 2:
        return out
    step = min(bars[i + 1][0] - bars[i][0] for i in range(min(50, len(bars) - 1)))
    tr = [0.0] * len(bars)
    vp = [0.0] * len(bars)
    vm = [0.0] * len(bars)
    ok = [False] * len(bars)
    for i in range(1, len(bars)):
        _, _, h, l, _ = bars[i]
        _, _, ph, pl, pc = bars[i - 1]
        tr[i] = max(h, pc) - min(l, pc)
        vp[i] = abs(h - pl)
        vm[i] = abs(l - ph)
        ok[i] = bars[i][0] - bars[i - 1][0] == step
    logn = math.log10(n)
    s_tr = s_vp = s_vm = 0.0
    bad = 0
    for i in range(1, len(bars)):
        s_tr += tr[i]; s_vp += vp[i]; s_vm += vm[i]; bad += (not ok[i])
        if i > n:
            j = i - n
            s_tr -= tr[j]; s_vp -= vp[j]; s_vm -= vm[j]; bad -= (not ok[j])
        if i < n or bad or s_tr <= 0:
            continue
        hi = max(b[2] for b in bars[i - n + 1:i + 1])
        lo = min(b[3] for b in bars[i - n + 1:i + 1])
        if hi <= lo:
            continue
        chop = 100.0 * math.log10(s_tr / (hi - lo)) / logn
        if chop >= th:
            continue
        if s_vp > s_vm:
            out[i] = 1
        elif s_vm > s_vp:
            out[i] = -1
    return out


def period_of(ms):
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()
    for name, (a, b) in PERIODS.items():
        if a <= d <= b:
            return name
    return None


def build_records(spot, perp_by_t, sig):
    """Záznam na signál: bar t+1 musí navazovat (krok) a mít perp bar se stejným časem."""
    recs = []
    step = spot[1][0] - spot[0][0]
    for i, d in sig.items():
        if i + 1 >= len(spot) or spot[i + 1][0] - spot[i][0] != step:
            continue
        t1, o, _, _, c = spot[i + 1]
        per = period_of(t1)
        if per is None:
            continue
        up = 1 if c >= o else -1
        prev_up = 1 if spot[i][4] >= spot[i][1] else -1
        pb = perp_by_t.get(t1)
        perp_ret = (pb[4] / pb[1] - 1.0) * d if pb else None
        recs.append({"t": t1, "period": per, "dir": d, "win": int(d == up), "up": up, "prev_up": prev_up,
                     "tiny": int(abs(c / o - 1.0) < TINY_MOVE), "perp_ret": perp_ret})
    recs.sort(key=lambda r: r["t"])
    return recs


# ------------------------------------------------------------------ statistiky
def wilson_low(k, n, z=1.959963984540054):
    if n == 0:
        return 0.0
    p = k / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    adj = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - adj) / den


def daily(values_by_t):
    d = {}
    for t, v in values_by_t:
        k = t // 86_400_000
        d[k] = d.get(k, 0.0) + v
    return [d[k] for k in sorted(d)]


def sharpe(xs):
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return m / math.sqrt(v) if v > 0 else 0.0


def max_dd(equity):
    peak, dd = -1e300, 0.0
    for e in equity:
        peak = max(peak, e)
        if peak > 0:
            dd = max(dd, 1 - e / peak)
    return dd


def stats_period(recs):
    n = len(recs)
    k = sum(r["win"] for r in recs)
    hr = k / n if n else 0.0
    z = (k - 0.5 * n) / math.sqrt(0.25 * n) if n else 0.0
    nt = [r for r in recs if not r["tiny"]]
    out = {"signals": n, "wins": k, "hit_rate": hr, "z_vs_50": z, "wilson_low95": wilson_low(k, n),
           "hit_rate_ex_tiny": (sum(r["win"] for r in nt) / len(nt)) if nt else None,
           "naive": {"continuation": (sum(r["prev_up"] == r["up"] for r in recs) / n) if n else None,
                     "reversal": (sum(r["prev_up"] != r["up"] for r in recs) / n) if n else None,
                     "always_up": (sum(r["up"] == 1 for r in recs) / n) if n else None}}
    trackP = {}
    for m in MULTS:
        q = 0.5 + m * COST_STEP
        rets = [(r["t"], (r["win"] / q) - 1.0) for r in recs]
        tot = sum(v for _, v in rets)
        trackP[f"x{m}"] = {"q": q, "net_per_1usd_bets": tot, "mean_per_bet": tot / n if n else 0.0,
                           "daily_sharpe": sharpe(daily(rets))}
    out["trackP"] = trackP
    trackF = {}
    pr = [r for r in recs if r["perp_ret"] is not None]
    for m in MULTS:
        pnl = [(r["t"], NOTIONAL * (r["perp_ret"] - m * PERP_COST)) for r in pr]
        gw = sum(v for _, v in pnl if v > 0)
        gl = -sum(v for _, v in pnl if v < 0)
        eq, e = [], NOTIONAL
        for v in daily(pnl):
            e += v
            eq.append(e)
        trackF[f"x{m}"] = {"trades": len(pnl), "net": sum(v for _, v in pnl),
                           "gross_edge_bps": (1e4 * sum(r["perp_ret"] for r in pr) / len(pr)) if pr else 0.0,
                           "pf": (gw / gl) if gl > 0 else None, "daily_sharpe": sharpe(daily(pnl)),
                           "max_dd": max_dd([NOTIONAL] + eq)}
    out["trackF"] = trackF
    return out


def buy_hold(perp, period):
    a, b = PERIODS[period]
    days = {}
    for t, o, h, l, c in perp:
        d = datetime.fromtimestamp(t / 1000, tz=timezone.utc).date().isoformat()
        if a <= d <= b:
            days.setdefault(d, [o, c])
            days[d][1] = c
    ks = sorted(days)
    if not ks:
        return None
    closes = [days[k][1] for k in ks]
    first = days[ks[0]][0]
    eq = [first] + closes
    rets = [eq[i] / eq[i - 1] - 1 for i in range(1, len(eq))]
    return {"return": closes[-1] / first - 1, "daily_sharpe": sharpe(rets), "max_dd": max_dd(eq)}


def dsr_daily(recs, mult):
    from tools.research.deflated_sharpe import dsr_from_returns
    q = 0.5 + mult * COST_STEP
    rets = daily([(r["t"], (r["win"] / q) - 1.0) for r in recs])
    return dsr_from_returns(rets, DSR_N, DSR_VAR_ANNUAL / 365) if len(rets) > 2 else {"dsr": 0.0}


# ------------------------------------------------------------------ hlavní
def evaluate(spot_by_tf, perp_by_tf):
    res = {"cells": {}, "selected": {}, "benchmark_bh_perp": {}, "verdict": {}}
    sel_recs = {}
    for tf in TFS:
        spot = spot_by_tf[tf]
        perp_by_t = {b[0]: b for b in perp_by_tf[tf]}
        best, best_z = None, -1e9
        cell_recs = {}
        for n, th in GRID:
            name = cell_name(tf, n, th)
            recs = build_records(spot, perp_by_t, signals(spot, n, th))
            cell_recs[name] = recs
            res["cells"][name] = {p: stats_period([r for r in recs if r["period"] == p]) for p in PERIODS}
            tun = res["cells"][name]["tuning"]
            if tun["signals"] >= MIN_SIGNALS and tun["z_vs_50"] > best_z:
                best, best_z = name, tun["z_vs_50"]
        res["selected"][tf] = best
        sel_recs[tf] = cell_recs.get(best, [])
        res["benchmark_bh_perp"][tf] = {p: buy_hold(perp_by_tf[tf], p) for p in PERIODS}
        if best is None:
            res["verdict"][tf] = {"verdict": "ZAMÍTNUTO", "reason": "žádná buňka s ≥ 1000 signály v ladění"}
            continue
        c = res["cells"][best]
        val_recs = [r for r in sel_recs[tf] if r["period"] == "validation"]
        dsr_info = dsr_daily(val_recs, 2)
        dsr = dsr_info["dsr"]
        v = c["validation"]
        best_naive = max(x for x in v["naive"].values() if x is not None)
        gates = {
            "P0_tuning_hit_ge_0.53": c["tuning"]["hit_rate"] >= 0.53,
            "P1_val_wilson_low_gt_0.52": v["wilson_low95"] > 0.52,
            "P2_val_hit_ge_best_naive_plus_1pp": v["hit_rate"] >= best_naive + 0.01,
            "P3_val_dsr_x2_ge_0.95": dsr >= 0.95,
            "P4_final_hit_gt_0.52": c["final_test"]["hit_rate"] > 0.52,
        }
        bh = res["benchmark_bh_perp"][tf]["validation"]
        fv, ff = v["trackF"]["x2"], c["final_test"]["trackF"]["x2"]
        gatesF = {
            "F_val_net_x2_gt_0": fv["net"] > 0,
            "F_val_pf_x2_gt_1.2": (fv["pf"] or 0) > 1.2,
            "F_val_sharpe_gt_bh": bh is not None and fv["daily_sharpe"] > bh["daily_sharpe"],
            "F_final_net_x2_gt_0": ff["net"] > 0,
        }
        passed = all(gates.values())
        res["verdict"][tf] = {"cell": best, "dsr_val_x2": dsr, "dsr_info": dsr_info, "best_naive_val": best_naive, "gates_P": gates,
                              "gates_F": gatesF,
                              "verdict": "DIAGNOSTIKA PROŠLA → forward PAPER" if passed else "ZAMÍTNUTO",
                              "failed": [k for k, ok in {**gates}.items() if not ok]}
    return res, sel_recs


def write_trades(path, sel_recs, res):
    with gzip.open(path, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tf", "cell", "period", "t_open_ms", "dir", "win", "up", "prev_up", "tiny", "perp_ret"])
        for tf in TFS:
            for r in sel_recs[tf]:
                w.writerow([tf, res["selected"][tf], r["period"], r["t"], r["dir"], r["win"], r["up"], r["prev_up"],
                            r["tiny"], "" if r["perp_ret"] is None else f"{r['perp_ret']:.10f}"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-a4")
    ap.add_argument("--outdir", default="research/vortex_chop")
    a = ap.parse_args()
    out = Path(a.outdir)
    manifest = []
    spot = {tf: load_series(SPOT, tf, a.cache, manifest) for tf in TFS}
    perp = {tf: load_series(PERP, tf, a.cache, manifest) for tf in TFS}
    res, sel = evaluate(spot, perp)
    res["params"] = {"grid": GRID, "tfs": TFS, "periods": PERIODS, "cost_step": COST_STEP, "perp_cost_x1": PERP_COST,
                     "dsr_n": DSR_N, "dsr_var_annual": DSR_VAR_ANNUAL, "protocol": "0c506a1"}
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    (out / "data_source.json").write_text(json.dumps({"archives": len(manifest), "files": manifest}, indent=0))
    write_trades(out / "trades.csv.gz", sel, res)
    for tf in TFS:
        v = res["verdict"][tf]
        print("A4_SUMMARY", tf, json.dumps(v, ensure_ascii=False))
        if res["selected"][tf]:
            for p in PERIODS:
                s = res["cells"][res["selected"][tf]][p]
                print("A4_PERIOD", tf, p, f"n={s['signals']} hit={s['hit_rate']:.4f} wl={s['wilson_low95']:.4f}",
                      "naive", json.dumps(s["naive"]), "P_x2", f"{s['trackP']['x2']['net_per_1usd_bets']:.1f}",
                      "F_x2", f"{s['trackF']['x2']['net']:.0f}", "F_edge_bps", f"{s['trackF']['x1']['gross_edge_bps']:.2f}",
                      "BH", json.dumps(res["benchmark_bh_perp"][tf][p]))
    for name, c in res["cells"].items():
        print("A4_CELL", name, " ".join(f"{p}:{c[p]['signals']}/{c[p]['hit_rate']:.4f}" for p in PERIODS))


if __name__ == "__main__":
    main()
