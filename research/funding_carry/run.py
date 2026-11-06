"""Delta-neutrální funding carry BTC/ETH (spot long + USDT-M perp short) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.funding_carry.run --cache /tmp/vision --outdir research/funding_carry
"""
import argparse
import csv
import hashlib
import io
import json
import math
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ASSETS = ("BTCUSDT", "ETHUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
GRID = (0.10, 0.20)
INFO = (0.05, 0.30)
NEIGHBOR = {0.10: 0.05, 0.20: 0.30}
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-27")}  # dodatek 2: perp 1d 2026-10-28 chybí
WF_YEARS = (2021, 2022, 2023, 2024)
SLEEVE = 5_000.0
M_LO, M_HI = 0.30, 0.70
OPEN_WINDOW_MS = 60_000
DSR_N, DSR_VAR_ANNUAL = 140, 0.5
DAY_MS = 86_400_000


# ------------------------------------------------------------------ data
def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def _csv_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]


def parse_klines(payload):
    bars = []
    for row in _csv_rows(payload):
        ts = int(row[0])
        if ts > 10 ** 14:  # µs
            ts //= 1000
        bars.append({"ts": ts, "open": float(row[1]), "high": float(row[2]),
                     "low": float(row[3]), "close": float(row[4])})
    return bars


def parse_funding(payload):
    """Binance Vision fundingRate: calc_time, funding_interval_hours, last_funding_rate."""
    out = []
    for row in _csv_rows(payload):
        ts = int(row[0])
        if ts > 10 ** 14:
            ts //= 1000
        out.append({"ts": ts, "interval_h": float(row[1]), "rate": float(row[2])})
    return out


def urls(asset):
    base = "https://data.binance.vision/data"
    for y, m in months():
        tag = f"{y}-{m:02d}"
        yield "spot", f"{base}/spot/monthly/klines/{asset}/1d/{asset}-1d-{tag}.zip"
        yield "perp", f"{base}/futures/um/monthly/klines/{asset}/1d/{asset}-1d-{tag}.zip"
        yield "funding", f"{base}/futures/um/monthly/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"


def load(cache, fetcher=fetch):
    market, manifest, missing = {}, [], []
    for a in ASSETS:
        series = {"spot": [], "perp": [], "funding": []}
        for kind, url in urls(a):
            p = Path(cache) / kind / url.rsplit("/", 1)[1]
            if not p.exists():
                try:
                    payload = fetcher(url)
                except urllib.error.HTTPError as e:
                    missing.append({"url": url, "http": e.code})
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(payload)
            payload = p.read_bytes()
            rows = parse_funding(payload) if kind == "funding" else parse_klines(payload)
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
            series[kind].extend(rows)
        for kind in ("spot", "perp"):
            dedup = {b["ts"]: b for b in series[kind]}
            series[kind] = {day(t): dedup[t] for t in sorted(dedup)}
            # dodatek protokolu (2026-11-06, před zobrazením výsledků): den chybějící v měsíčním archivu
            # se doplní z oficiálního DENNÍHO archivu Binance Vision (stejný zdroj, SHA-256 do manifestu)
            need = daterange(date(2020, 8, 24), date.fromisoformat(PERIODS["final_test"][1]))
            for d in need:
                if d in series[kind]:
                    continue
                base = "spot" if kind == "spot" else "futures/um"
                url = (f"https://data.binance.vision/data/{base}/daily/klines/{a}/1d/"
                       f"{a}-1d-{d.isoformat()}.zip")
                pth = Path(cache) / f"{kind}-daily" / url.rsplit("/", 1)[1]
                if not pth.exists():
                    try:
                        payload = fetcher(url)
                    except urllib.error.HTTPError as e:
                        missing.append({"url": url, "http": e.code, "required": True})
                        continue
                    pth.parent.mkdir(parents=True, exist_ok=True)
                    pth.write_bytes(payload)
                payload = pth.read_bytes()
                rows = parse_klines(payload)
                manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows),
                                 "filled_missing_day": d.isoformat()})
                print("FILLED_FROM_DAILY", kind, a, d.isoformat(), len(rows))
                for b in rows:
                    series[kind][day(b["ts"])] = b
        fd = {f["ts"]: f for f in series["funding"]}
        series["funding"] = [fd[t] for t in sorted(fd)]
        market[a] = series
    return market, manifest, missing


def day(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).date()


def day_start_ms(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def funding_by_day(funding):
    out = {}
    for f in funding:
        out.setdefault(day(f["ts"]), []).append(f)
    return out


def f7_series(fbd, days):
    """f7(t) = průměr anualizovaných sazeb událostí ve dnech t-6..t (vše ≤ konec dne t)."""
    out = {}
    for t in days:
        ev = []
        for k in range(7):
            ev.extend(fbd.get(t - timedelta(days=k), []))
        if not ev:
            raise ValueError(f"žádný funding v okně 7 dní před {t}")
        out[t] = sum(e["rate"] * (24.0 / e["interval_h"]) * 365.0 for e in ev) / len(ev)
    return out


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# ------------------------------------------------------------------ simulace jednoho rukávu
def simulate_sleeve(series, asset, start, end, mult, H, capital=SLEEVE, variant=""):
    """Vrací (episodes, curve{den: hodnota k close}, final_value). Viz PROTOCOL.md."""
    c = (FEE + SLIP) * mult
    spot, perp = series["spot"], series["perp"]
    fbd = funding_by_day(series["funding"])
    days = list(daterange(start, end))
    for d in days:
        if d not in spot or d not in perp:
            raise ValueError(f"chybí klines {asset} {d}")
    f7 = f7_series(fbd, days)

    cash = capital
    pos = None  # dict(q, margin, entry_p, ...)
    pending = None
    episodes, curve = [], {}

    def close_pos(ps, pp, d, reason, liquidated=False):
        nonlocal cash, pos
        perp_val = 0.0 if liquidated else pos["margin"] + pos["q"] * (pos["entry_p"] - pp)
        legs = 1 if liquidated else 2
        cost = pos["q"] * c * (ps + (pp if legs == 2 else 0.0))
        value = pos["q"] * ps + perp_val - cost
        pos["costs"] += cost
        episodes.append({"variant": variant, "asset": asset, "cost_mult": mult,
                         "entry_date": pos["entry_date"].isoformat(), "exit_date": d.isoformat(),
                         "exit_reason": reason, "days": (d - pos["entry_date"]).days,
                         "start_value": round(pos["start_value"], 6), "end_value": round(value, 6),
                         "funding": round(pos["funding"], 6), "costs": round(pos["costs"], 6),
                         "rebalances": pos["rebalances"], "liquidated": int(liquidated),
                         "net_pnl": round(value - pos["start_value"], 6)})
        cash, pos = value, None

    for i, d in enumerate(days):
        b_s, b_p = spot[d], perp[d]
        held_over_open = pos is not None
        # 1) akce za open(d)
        if pending == "enter" and pos is None:
            o_s, o_p = b_s["open"], b_p["open"]
            q = cash / (2 * o_s + c * (o_s + o_p))
            cost = q * c * (o_s + o_p)
            pos = {"q": q, "margin": cash - q * o_s - cost, "entry_p": o_p, "entry_date": d,
                   "start_value": cash, "funding": 0.0, "costs": cost, "rebalances": 0}
            cash = 0.0
        elif pending == "exit" and pos is not None:
            close_pos(b_s["open"], b_p["open"], d, "signal")
            held_over_open = False
        elif pending == "rebalance" and pos is not None:
            o_s, o_p = b_s["open"], b_p["open"]
            E = pos["q"] * o_s + pos["margin"] + pos["q"] * (pos["entry_p"] - o_p)
            q2 = E / (2 * o_s)
            cost = abs(q2 - pos["q"]) * c * (o_s + o_p)
            q2 = (E - cost) / (2 * o_s)
            cost = abs(q2 - pos["q"]) * c * (o_s + o_p)
            pos.update(q=q2, margin=E - cost - q2 * o_s, entry_p=o_p)
            pos["costs"] += cost
            pos["rebalances"] += 1
        pending = None
        liquidated_today = False
        # 2) funding dne d (00:00 jen pokud pozice trvala přes open), likvidace podle high
        if pos is not None:
            ds = day_start_ms(d)
            for e in fbd.get(d, []):
                if e["ts"] - ds < OPEN_WINDOW_MS and not held_over_open:
                    continue
                amt = e["rate"] * pos["q"] * b_p["close"]
                pos["margin"] += amt
                pos["funding"] += amt
            if pos["q"] * (b_p["high"] - pos["entry_p"]) >= pos["margin"]:
                close_pos(b_s["close"], b_p["close"], d, "liquidation", liquidated=True)
                liquidated_today = True
        # 3) ocenění k close, konec období, signály pro d+1
        last = i == len(days) - 1
        if pos is not None and last:
            close_pos(b_s["close"], b_p["close"], d, "period_end")
        if pos is not None:
            S = pos["q"] * b_s["close"]
            M = pos["margin"] + pos["q"] * (pos["entry_p"] - b_p["close"])
            curve[d] = S + M
            if f7[d] < 0:
                pending = "exit"
            elif not (M_LO <= M / (S + M) <= M_HI):
                pending = "rebalance"
        else:
            curve[d] = cash
            if not last and not liquidated_today and f7[d] > H:
                pending = "enter"
    return episodes, curve, cash


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


def trade_metrics(eps):
    pnl = [e["net_pnl"] for e in eps]
    gains = sum(p for p in pnl if p > 0)
    losses = -sum(p for p in pnl if p < 0)
    top3 = sum(sorted(pnl, reverse=True)[:3])
    return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
            "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
            "net_without_top3": round(sum(pnl) - top3, 4),
            "funding": round(sum(e["funding"] for e in eps), 4),
            "costs": round(sum(e["costs"] for e in eps), 4),
            "liquidations": sum(e["liquidated"] for e in eps)}


def run_basket(market, start, end, mult, H, variant):
    eps, curves, final = [], [], 0.0
    for a in ASSETS:
        e, cv, f = simulate_sleeve(market[a], a, start, end, mult, H, variant=variant)
        eps += e
        curves.append(cv)
        final += f
    curve = {d: sum(cv[d] for cv in curves) for d in curves[0]}
    cm, rets = curve_metrics(curve, 2 * SLEEVE)
    out = {**cm, **trade_metrics(eps), "final_value": round(final, 4)}
    return out, eps, rets


def buy_hold(market, start, end, mult):
    c = (FEE + SLIP) * mult
    qty = {a: SLEEVE * (1 - c) / market[a]["spot"][start]["open"] for a in ASSETS}
    curve = {d: sum(qty[a] * market[a]["spot"][d]["close"] for a in ASSETS) for d in daterange(start, end)}
    curve[end] *= (1 - c)
    cm, _ = curve_metrics(curve, 2 * SLEEVE)
    return {**cm, "net_pnl": round(curve[end] - 2 * SLEEVE, 4)}


def pdate(s):
    return date.fromisoformat(s)


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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision")
    ap.add_argument("--outdir", default="research/funding_carry")
    args = ap.parse_args(argv)
    out = Path(args.outdir)
    market, manifest, missing = load(args.cache)
    (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
    if missing:
        print("MISSING_ARCHIVES", json.dumps(missing[:20]), "count", len(missing))
        # chybějící měsíce mimo potřebné okno (2020-08-25 … 2026-10-31) jsou povoleny jen pro klines před 2020-08
        bad = [m for m in missing if m.get("required") or not any(f"-{y}-{mm:02d}.zip" in m["url"]
                                             for y, mm in [(2020, k) for k in range(1, 8)])]
        if bad:
            print("FATAL missing archives in required window", json.dumps(bad[:20]))
            sys.exit(2)

    all_rows, results, bh = [], {}, {}
    # výběr H na ladění ×1
    tune = {}
    for H in GRID + INFO:
        r, eps, _ = run_basket(market, pdate(PERIODS["tuning"][0]), pdate(PERIODS["tuning"][1]), 1, H, f"H{int(H*100)}")
        tune[H] = r
    chosen = max(GRID, key=lambda h: tune[h]["net_pnl"])
    tag = f"H{int(chosen*100)}"
    val_rets = None
    for H in GRID + INFO:
        vt = f"H{int(H*100)}"
        results[vt] = {}
        for p, (s, e) in PERIODS.items():
            results[vt][p] = {}
            for m in COST_MULTIPLIERS:
                if H != chosen and not (m == 2 and p == "validation") and not (p == "tuning" and m == 1):
                    continue
                r, eps, rets = run_basket(market, pdate(s), pdate(e), m, H, vt)
                results[vt][p][f"x{m}"] = r
                for ep in eps:
                    all_rows.append({"period": p, **ep})
                if H == chosen and p == "validation" and m == 1:
                    val_rets = rets
    for p, (s, e) in PERIODS.items():
        bh[p] = {f"x{m}": buy_hold(market, pdate(s), pdate(e), m) for m in COST_MULTIPLIERS}
    wf = {}
    for y in WF_YEARS:
        r, eps, _ = run_basket(market, date(y, 1, 1), date(y, 12, 31), 2, chosen, tag)
        wf[str(y)] = r
        for ep in eps:
            all_rows.append({"period": f"wf_{y}", **ep})

    res = results[tag]
    track_a, track_b = evaluate(res, bh)
    passed_a, passed_b = all(track_a.values()), all(track_b.values())
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    dsr = dsr_from_returns(val_rets, DSR_N, DSR_VAR_ANNUAL / 365)
    neighbor = results[f"H{int(NEIGHBOR[chosen]*100)}"]["validation"]["x2"]["net_pnl"]
    wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
    robust = {"dsr_ge_0_95": dsr["dsr"] >= 0.95, "neighbor_val_x2_profit": neighbor > 0,
              "walk_forward_ge_3_of_4": wf_pos >= 3}
    verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
    payload = {"protocol": "research/funding_carry/PROTOCOL.md", "chosen_H": chosen,
               "tuning_selection_x1": {f"H{int(h*100)}": tune[h] for h in GRID + INFO},
               "strategy": results, "buy_hold_50_50": bh, "walk_forward_x2": wf,
               "track_a": track_a, "track_b": track_b, "passed_a": passed_a, "passed_b": passed_b,
               "dsr_validation_x1": dsr, "robustness": robust, "verdict": verdict}
    (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
    cols = ["period", "variant", "asset", "cost_mult", "entry_date", "exit_date", "exit_reason", "days",
            "start_value", "end_value", "funding", "costs", "rebalances", "liquidated", "net_pnl"]
    with open(out / "trades.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(all_rows)
    print("SUMMARY", json.dumps({"chosen_H": chosen, "verdict": verdict, "track_a": track_a, "track_b": track_b,
                                 "robust": robust, "dsr": round(dsr["dsr"], 4),
                                 "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
                                 "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
                                 "wf": {k: v["net_pnl"] for k, v in wf.items()}}, default=str))


if __name__ == "__main__":
    main()
