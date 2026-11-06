"""Spot-led price discovery spot → USDT-M perp, 5m, BTC/ETH/XRP (H-20261106-3) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.spot_led.run --cache /tmp/vision-5m --outdir research/spot_led
"""
import argparse
import bisect
import csv
import hashlib
import heapq
import io
import json
import math
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
GRID = [(th, hold) for th in (0.65, 0.70) for hold in (15, 30)]  # (p_hi; p_lo = 1 − p_hi, držení min)
R_SPOT, R_PERP = 0.002, 0.001
PERIODS = {"tuning": ("2020-02-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
FRACTION = 0.10
DSR_N, DSR_VAR_ANNUAL = 159, 0.5
BAR = 300_000
HOUR_MS = 3_600_000
DAY_MS = 86_400_000


def vt(th, hold):
    return f"P{int(round(th * 100))}_H{hold}"


# ------------------------------------------------------------------ data
def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _csv_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


def parse_spot(payload):
    """→ [(ts, close, volume, taker_buy_base)]"""
    return [(_ms(int(r[0])), float(r[4]), float(r[5]), float(r[9])) for r in _csv_rows(payload)]


def parse_perp(payload):
    """→ [(ts, open, close)]"""
    return [(_ms(int(r[0])), float(r[1]), float(r[4])) for r in _csv_rows(payload)]


def normalize_funding_ts(ts):
    near = round(ts / HOUR_MS) * HOUR_MS
    if abs(ts - near) > 1000:
        raise ValueError(f"funding timestamp {ts} je {ts - near} ms od celé hodiny")
    return near


def parse_funding(payload):
    return [(normalize_funding_ts(_ms(int(r[0]))), float(r[2])) for r in _csv_rows(payload)]


def urls(asset):
    b = "https://data.binance.vision/data"
    for y, m in months():
        tag = f"{y}-{m:02d}"
        yield "spot", (y, m), f"{b}/spot/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
        yield "perp", (y, m), f"{b}/futures/um/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
        yield "fr", (y, m), f"{b}/futures/um/monthly/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"


def load(cache, fetcher=fetch):
    market, manifest, missing, fatal = {}, [], [], []
    parsers = {"spot": parse_spot, "perp": parse_perp, "fr": parse_funding}
    for a in ASSETS:
        raw = {"spot": {}, "perp": {}, "fr": {}}
        present, miss = {k: [] for k in raw}, {k: [] for k in raw}
        for kind, ym, url in urls(a):
            p = Path(cache) / kind / url.rsplit("/", 1)[1]
            if not p.exists():
                try:
                    payload = fetcher(url)
                except urllib.error.HTTPError as e:
                    missing.append({"url": url, "http": e.code})
                    miss[kind].append(ym)
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(payload)
            payload = p.read_bytes()
            present[kind].append(ym)
            rows = parsers[kind](payload)
            for r in rows:
                raw[kind][r[0]] = r[1:] if kind != "fr" else r[1]
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
        for kind in raw:
            if present[kind]:
                first = min(present[kind])
                fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
            else:
                fatal.append({"asset": a, "kind": kind, "month": "all"})
        market[a] = prepare(raw["spot"], raw["perp"], raw["fr"])
    return market, manifest, missing, fatal


def prepare(spot, perp, fund):
    """spot {ts: (close, vol, taker_buy)}, perp {ts: (open, close)}, fund {ts: rate}."""
    perp_ts = sorted(perp)
    return {"spot": spot, "perp": perp, "perp_ts": perp_ts, "funding": dict(sorted(fund.items())),
            "features": features(spot, perp)}


def features(spot, perp):
    """Pro každý spot čas T se svíčkami T a T−5m v obou trzích: (T, podíl, r_spot, r_perp). Jen data ≤ T."""
    out = []
    for T in sorted(spot):
        s, sp = spot[T], spot.get(T - BAR)
        p, pp = perp.get(T), perp.get(T - BAR)
        if sp is None or p is None or pp is None or s[1] <= 0 or sp[0] <= 0 or pp[1] <= 0:
            continue
        out.append((T, s[2] / s[1], s[0] / sp[0] - 1, p[1] / pp[1] - 1))
    return out


def gap_audit(m):
    spot, perp = m["spot"], m["perp"]
    def missing(ts_sorted):
        return sum(max(0, (b - a) // BAR - 1) for a, b in zip(ts_sorted, ts_sorted[1:]))
    ss = set(spot)
    ps = set(perp)
    return {"spot_bars": len(spot), "perp_bars": len(perp), "spot_missing_5m": missing(sorted(spot)),
            "perp_missing_5m": missing(m["perp_ts"]), "spot_only": len(ss - ps), "perp_only": len(ps - ss),
            "usable_signal_bars": len(m["features"])}


# ------------------------------------------------------------------ simulace
def ms_of(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def date_of(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def perp_price_at(m, t):
    """open svíčky v t; chybí-li, close poslední dřívější svíčky."""
    b = m["perp"].get(t)
    if b is not None:
        return b[0]
    i = bisect.bisect_left(m["perp_ts"], t) - 1
    if i < 0:
        raise KeyError(t)
    return m["perp"][m["perp_ts"][i]][1]


def candidates(m, asset, start_ms, end_ms, th, hold):
    """Kandidátní obchody jednoho aktiva (nezávislé na equity): bez překryvu, výstup uvnitř období."""
    hold_ms = hold * 60_000
    out, free_from = [], -1
    feats = m["features"]
    i = bisect.bisect_left(feats, (start_ms - BAR,))  # vstup (T+5m) ≥ start
    for T, share, rs, rp in feats[i:]:
        entry_t = T + BAR
        if entry_t >= end_ms:
            break
        if entry_t < start_ms or entry_t < free_from:
            continue
        if share > th and rs > R_SPOT and rp < R_PERP:
            side = 1
        elif share < 1 - th and rs < -R_SPOT and rp > -R_PERP:
            side = -1
        else:
            continue
        if entry_t not in m["perp"]:
            continue
        planned = entry_t + hold_ms
        j = bisect.bisect_left(m["perp_ts"], planned)
        if j >= len(m["perp_ts"]):
            continue
        exit_t = m["perp_ts"][j]
        if exit_t >= end_ms:
            continue
        f_unit = 0.0
        # funding: události s entry_t < t < exit_t
        lo = (entry_t // HOUR_MS + 1) * HOUR_MS
        t = lo
        while t < exit_t:
            if t in m["funding"]:
                f_unit += -side * m["funding"][t] * perp_price_at(m, t)
            t += HOUR_MS
        out.append({"asset": asset, "side": side, "signal_ts": T, "entry_ts": entry_t, "exit_ts": exit_t,
                    "entry": m["perp"][entry_t][0], "exit": m["perp"][exit_t][0], "funding_unit": f_unit,
                    "share": share, "r_spot": rs, "r_perp": rp, "data_gap": int(exit_t != planned)})
        free_from = exit_t
    return out


def simulate(market, start, end, th, hold, mult, variant=""):
    """Sdílená equity: notional = 10 % realizované equity při vstupu. Vrací (obchody, denní equity)."""
    c = (FEE + SLIP) * mult
    s_ms, e_ms = ms_of(start), ms_of(end) + DAY_MS
    cands = sorted((x for a in ASSETS for x in candidates(market[a], a, s_ms, e_ms, th, hold)),
                   key=lambda x: (x["entry_ts"], x["asset"]))
    cash, pending, trades = START_EQUITY, [], []
    realized_by_day = {}
    for x in cands:
        while pending and pending[0][0] <= x["entry_ts"]:
            _, _, tr = heapq.heappop(pending)
            cash += tr["net_pnl"]
        notional = FRACTION * cash
        qty = notional / x["entry"]
        gross = x["side"] * qty * (x["exit"] - x["entry"])
        costs = notional * c + qty * x["exit"] * c
        fund = qty * x["funding_unit"]
        tr = {**x, "variant": variant, "cost_mult": mult, "qty": qty, "notional": notional, "gross": gross,
              "funding": fund, "costs": costs, "net_pnl": gross + fund - costs,
              "gross_bp": x["side"] * (x["exit"] / x["entry"] - 1) * 1e4}
        trades.append(tr)
        heapq.heappush(pending, (x["exit_ts"], len(trades), tr))
    for tr in trades:
        d = date_of(tr["exit_ts"])
        realized_by_day[d] = realized_by_day.get(d, 0.0) + tr["net_pnl"]
    curve, eq, d = {}, START_EQUITY, start
    while d <= end:
        eq += realized_by_day.get(d, 0.0)
        curve[d] = eq
        d += timedelta(days=1)
    return trades, curve


# ------------------------------------------------------------------ metriky
def curve_metrics(curve, start_value):
    vals = [curve[d] for d in sorted(curve)]
    rets = [vals[0] / start_value - 1] + [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    peak, mdd = start_value, 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    return {"return_pct": round((vals[-1] / start_value - 1) * 100, 4),
            "sharpe": round(mu / sd * math.sqrt(365), 4) if sd > 0 else 0.0,
            "max_drawdown_pct": round(mdd * 100, 4)}, rets


def trade_metrics(trades, start, end):
    pnl = [t["net_pnl"] for t in trades]
    gains = sum(p for p in pnl if p > 0)
    losses = -sum(p for p in pnl if p < 0)
    top3 = sum(sorted(pnl, reverse=True)[:3])
    years = max((end - start).days + 1, 1) / 365.25
    return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
            "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
            "net_without_top3": round(sum(pnl) - top3, 4),
            "funding": round(sum(t["funding"] for t in trades), 4),
            "costs": round(sum(t["costs"] for t in trades), 4),
            "long_trades": sum(1 for t in trades if t["side"] == 1),
            "short_trades": sum(1 for t in trades if t["side"] == -1),
            "data_gap_exits": sum(t["data_gap"] for t in trades),
            "avg_gross_bp": round(sum(t["gross_bp"] for t in trades) / len(trades), 3) if trades else None,
            "trades_per_year_per_asset": {a: round(sum(1 for t in trades if t["asset"] == a) / years, 1)
                                          for a in ASSETS}}


def run(market, start, end, mult, th, hold, variant):
    trades, curve = simulate(market, start, end, th, hold, mult, variant)
    cm, rets = curve_metrics(curve, START_EQUITY)
    return {**cm, **trade_metrics(trades, start, end)}, trades, rets


def day_close(m, d):
    t = ms_of(d) + DAY_MS
    i = bisect.bisect_left(m["perp_ts"], t) - 1
    return m["perp"][m["perp_ts"][i]][1]


def buy_hold(market, start, end, mult):
    c = (FEE + SLIP) * mult
    t0 = ms_of(start)
    qty = {}
    for a in ASSETS:
        m = market[a]
        j = bisect.bisect_left(m["perp_ts"], t0)
        qty[a] = START_EQUITY / len(ASSETS) * (1 - c) / m["perp"][m["perp_ts"][j]][0]
    curve, d = {}, start
    while d <= end:
        curve[d] = sum(q * day_close(market[a], d) for a, q in qty.items())
        d += timedelta(days=1)
    curve[end] *= (1 - c)
    cm, _ = curve_metrics(curve, START_EQUITY)
    return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4)}


def evaluate(res, bh):
    v1, v2 = res["validation"]["x1"], res["validation"]["x2"]
    f2, t1 = res["final_test"]["x2"], res["tuning"]["x1"]
    bv, bf = bh["validation"]["x1"], bh["final_test"]["x2"]
    a = {"A1_sharpe_dd": v1["sharpe"] > bv["sharpe"] and v1["max_drawdown_pct"] < bv["max_drawdown_pct"],
         "A2_trades_ge_30": v1["trades"] >= 30,
         "A3_x2_pf_profit": (v2["profit_factor"] or 0) > 1.2 and v2["net_pnl"] > 0,
         "A4_wo_top3": v1["net_without_top3"] > 0,
         "A5_final_x2": f2["net_pnl"] > 0 and f2["sharpe"] > bf["sharpe"]
         and f2["max_drawdown_pct"] < bf["max_drawdown_pct"]}
    b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and (v2["profit_factor"] or 0) > 1.2,
         "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bv["max_drawdown_pct"]
         and res["final_test"]["x1"]["max_drawdown_pct"] <= 0.6 * bh["final_test"]["x1"]["max_drawdown_pct"],
         "B3_final_x2_profit": f2["net_pnl"] > 0,
         "B4_val_wo_top3": v1["net_without_top3"] > 0,
         "B5_trades_ge_20": v1["trades"] + res["final_test"]["x1"]["trades"] >= 20,
         "B6_tuning_x1_profit": t1["net_pnl"] > 0}
    return a, b


def neighbors(th, hold):
    return [(t2, h2) for (t2, h2) in GRID if (t2 == th) != (h2 == hold)]


def pdate(s):
    return date.fromisoformat(s)


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def trade_row(period, t):
    return {"period": period, "variant": t["variant"], "cost_mult": t["cost_mult"], "asset": t["asset"],
            "side": "LONG" if t["side"] == 1 else "SHORT", "signal_bar_utc": iso(t["signal_ts"]),
            "entry_utc": iso(t["entry_ts"]), "exit_utc": iso(t["exit_ts"]), "entry": t["entry"], "exit": t["exit"],
            "taker_buy_share": round(t["share"], 6), "r_spot": round(t["r_spot"], 6), "r_perp": round(t["r_perp"], 6),
            "qty": round(t["qty"], 10), "notional": round(t["notional"], 6), "gross": round(t["gross"], 6),
            "funding": round(t["funding"], 6), "costs": round(t["costs"], 6), "data_gap": t["data_gap"],
            "net_pnl": round(t["net_pnl"], 6)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-5m")
    ap.add_argument("--outdir", default="research/spot_led")
    args = ap.parse_args(argv)
    out = Path(args.outdir)
    market, manifest, missing, fatal = load(args.cache)
    (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
    if fatal:
        print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
        sys.exit(2)
    audit = {a: gap_audit(market[a]) for a in ASSETS}
    print("GAP_AUDIT", json.dumps(audit))

    rows, results, tune, rets_store = [], {}, {}, {}
    for (th, hold) in GRID:
        tag = vt(th, hold)
        results[tag] = {}
        for p, (s, e) in PERIODS.items():
            results[tag][p] = {}
            for m in COST_MULTIPLIERS:
                r, trades, rets = run(market, pdate(s), pdate(e), m, th, hold, tag)
                results[tag][p][f"x{m}"] = r
                rets_store[(tag, p, m)] = rets
                rows += [trade_row(p, t) for t in trades]
        tune[tag] = results[tag]["tuning"]["x1"]
    chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
    ctag = vt(*chosen)
    bh = {p: {f"x{m}": buy_hold(market, pdate(s), pdate(e), m) for m in COST_MULTIPLIERS}
          for p, (s, e) in PERIODS.items()}
    wf = {}
    for y in WF_YEARS:
        r, trades, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag)
        wf[str(y)] = r
        rows += [trade_row(f"wf_{y}", t) for t in trades]

    res = results[ctag]
    track_a, track_b = evaluate(res, bh)
    passed_a, passed_b = all(track_a.values()), all(track_b.values())
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    dsr = dsr_from_returns(rets_store[(ctag, "validation", 1)], DSR_N, DSR_VAR_ANNUAL / 365)
    nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
    wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
    robust = {"dsr_ge_0_95": dsr["dsr"] >= 0.95, "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
              "walk_forward_ge_3_of_4": wf_pos >= 3}
    verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
    payload = {"protocol": "research/spot_led/PROTOCOL.md", "chosen": ctag, "tuning_selection_x1": tune,
               "strategy": results, "buy_hold_equal_3": bh, "walk_forward_x2": wf, "neighbors_val_x2": nb,
               "track_a": track_a, "track_b": track_b, "passed_a": passed_a, "passed_b": passed_b,
               "dsr_validation_x1": dsr, "robustness": robust, "gap_audit": audit, "verdict": verdict}
    (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
    with open(out / "trades.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
        w.writeheader()
        w.writerows(rows)
    if (out / "trades.csv").stat().st_size > 50 * 2 ** 20:  # limit souborů GitHubu
        import gzip
        with open(out / "trades.csv", "rb") as src, gzip.open(out / "trades.csv.gz", "wb") as dst:
            dst.write(src.read())
        (out / "trades.csv").unlink()
    print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
                                 "robust": robust, "dsr": round(dsr["dsr"], 4), "neighbors": nb,
                                 "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
                                 "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
                                 "wf": {k: v["net_pnl"] for k, v in wf.items()}}, default=str))


if __name__ == "__main__":
    main()
