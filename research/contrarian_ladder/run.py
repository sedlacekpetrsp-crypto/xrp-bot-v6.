"""Kontrariánský žebřík podle propadu od 365denního maxima, 8 aktiv — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.contrarian_ladder.run --cache /tmp/vision-1d --outdir research/contrarian_ladder

Loader a metriky převzaty z research/near_high/run.py (PR #28). Simulace nová: 8 nezávislých rukávů,
každý = základ 50 % (buy & hold) + žebřík 50 % hotovosti (tranše R/3 při DD ≥ L[j], reset při novém max365).
"""
import argparse
import csv
import hashlib
import io
import json
import math
import sys
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT")
FIRST_MONTH = (2019, 8)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
LEVELS = (0.20, 0.30, 0.40)
NEIGHBORS = {"L15_25_35": (0.15, 0.25, 0.35), "L25_35_45": (0.25, 0.35, 0.45)}
LOOKBACK = 365
BASE_SHARE = 0.5
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
DSR_N, DSR_VAR_ANNUAL = 162, 0.5


# ------------------------------------------------------------------ data (jako PR #28)
def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def parse(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    bars = []
    for row in csv.reader(io.StringIO(text)):
        if not row or not row[0].strip().isdigit():
            continue
        ts = int(row[0])
        if ts > 10 ** 14:  # od 2025 µs
            ts //= 1000
        bars.append({"ts": ts, "open": float(row[1]), "high": float(row[2]),
                     "low": float(row[3]), "close": float(row[4])})
    return bars


def load(cache, fetcher=fetch):
    market, manifest = {}, []
    for s in SYMBOLS:
        bars = []
        for y, m in months():
            name = f"{s}-1d-{y}-{m:02d}.zip"
            url = f"https://data.binance.vision/data/spot/monthly/klines/{s}/1d/{name}"
            p = Path(cache) / name
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(fetcher(url))
            payload = p.read_bytes()
            b = parse(payload)
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "bars": len(b)})
            bars.extend(b)
        dedup = {b["ts"]: b for b in bars}
        market[s] = [dedup[t] for t in sorted(dedup)]
    return market, manifest


def day(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).date()


def by_day(bars):
    return {day(b["ts"]): b for b in bars}


# ------------------------------------------------------------------ signál
def drawdown_series(bars, lookback=LOOKBACK):
    """DD(t) = 1 − close(t)/max(close(t−lookback+1 … t)); jen dny s plným oknem bez mezer."""
    closes = [(day(b["ts"]), b["close"]) for b in bars]
    out = {}
    for i in range(lookback - 1, len(closes)):
        if (closes[i][0] - closes[i - lookback + 1][0]).days != lookback - 1:
            continue
        mx = max(c for _, c in closes[i - lookback + 1:i + 1])
        out[closes[i][0]] = 1 - closes[i][1] / mx
    return out


# ------------------------------------------------------------------ simulace jednoho rukávu
def simulate_sleeve(bars_by_day, dd, start, end, mult, capital, levels=LEVELS, ladder=True, asset=""):
    """Vrací (rows, curve{den: hodnota rukávu}). ladder=False ⇒ jen základ (statický 50/50)."""
    fee, slip = FEE * mult, SLIP * mult
    k_buy = 1 / ((1 + slip) * (1 + fee))     # množství za 1 USDT
    k_sell = (1 - slip) * (1 - fee)          # USDT za 1 USDT hodnoty
    days, d = [], start
    while d <= end:
        if d not in bars_by_day:
            raise ValueError(f"chybí svíčka {asset} {d}")
        days.append(d)
        d += timedelta(days=1)
    o0 = bars_by_day[start]["open"]
    base_cost = capital * BASE_SHARE
    base_qty = base_cost * k_buy / o0
    cash = capital - base_cost
    rows, curve = [], {}
    tranches = []            # otevřené tranše: {qty, cost, entry_day, dd_entry, level}
    n, reserve = 0, 0.0
    pending_buy, pending_reset = [], False
    for j, d in enumerate(days):
        o = bars_by_day[d]["open"]
        if pending_reset:
            for t in tranches:
                ev = t["qty"] * o * k_sell
                rows.append(_row(asset, "TRANCHE", t, d, ev, t["qty"] * o * (1 - k_sell)))
                cash += ev
            tranches, n, pending_reset = [], 0, False
        for lvl_idx in pending_buy:
            if n == 0:
                reserve = cash
            amt = cash if lvl_idx == len(levels) - 1 else min(reserve / len(levels), cash)
            if amt > 0:
                q = amt * k_buy / o
                cash -= amt
                tranches.append({"qty": q, "cost": amt, "entry_day": d, "level": levels[lvl_idx],
                                 "dd_entry": dd.get(d - timedelta(days=1)), "fee_in": amt * (1 - k_buy)})
            n = lvl_idx + 1
        pending_buy = []
        c = bars_by_day[d]["close"]
        if j == len(days) - 1:
            for t in tranches:
                ev = t["qty"] * c * k_sell
                rows.append(_row(asset, "TRANCHE", t, d, ev, t["qty"] * c * (1 - k_sell)))
                cash += ev
            bev = base_qty * c * k_sell
            rows.append(_row(asset, "BASE", {"qty": base_qty, "cost": base_cost, "entry_day": start, "level": None,
                                             "dd_entry": dd.get(start - timedelta(days=1)),
                                             "fee_in": base_cost * (1 - k_buy)},
                             d, bev, base_qty * c * (1 - k_sell)))
            curve[d] = cash + bev
            break
        curve[d] = cash + base_qty * c + sum(t["qty"] * c for t in tranches)
        if not ladder:
            continue
        x = dd.get(d)
        if x is None:
            raise ValueError(f"chybí DD {asset} {d}")
        if n > 0 and x <= 0.0:
            pending_reset = True
        elif n < len(levels):
            pending_buy = [i for i in range(n, len(levels)) if x >= levels[i]]
    return rows, curve


def _row(asset, kind, t, exit_day, end_value, fee_out):
    # fee_in = cost − (qty × open) = náklady nákupu v USDT (k_buy zahrnuje poplatek i skluz)
    return {"asset": asset, "kind": kind, "level": t["level"],
            "entry_day": t["entry_day"].isoformat(), "exit_day": exit_day.isoformat(),
            "dd_entry": round(t["dd_entry"], 4) if t["dd_entry"] is not None else None,
            "start_value": t["cost"], "end_value": end_value,
            "net_pnl": end_value - t["cost"], "fees": t["fee_in"] + fee_out,
            "gross_pnl": end_value - t["cost"] + t["fee_in"] + fee_out}


def simulate(market, dds, start, end, mult, levels=LEVELS, ladder=True, symbols=SYMBOLS, equity=START_EQUITY):
    px = {s: by_day(market[s]) for s in symbols}
    cap = equity / len(symbols)
    rows, total = [], {}
    for s in symbols:
        r, cv = simulate_sleeve(px[s], dds[s], start, end, mult, cap, levels, ladder, s)
        rows.extend(r)
        for d, v in cv.items():
            total[d] = total.get(d, 0.0) + v
    return rows, total


def buy_hold_basket(market, start, end, mult, symbols=SYMBOLS, equity=START_EQUITY):
    fee, slip = FEE * mult, SLIP * mult
    px = {s: by_day(market[s]) for s in symbols}
    q = {s: (equity / len(symbols)) / (px[s][start]["open"] * (1 + slip) * (1 + fee)) for s in symbols}
    curve, d = {}, start
    while d <= end:
        v = sum(q[s] * px[s][d]["close"] for s in symbols)
        if d == end:
            v *= (1 - slip) * (1 - fee)
        curve[d] = v
        d += timedelta(days=1)
    return curve


# ------------------------------------------------------------------ metriky
def daily_returns(curve, start_equity):
    vals = [curve[d] for d in sorted(curve)]
    return [vals[0] / start_equity - 1] + [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]


def metrics(curve, rows, start_equity=START_EQUITY):
    vals = [curve[d] for d in sorted(curve)]
    rets = daily_returns(curve, start_equity)
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    peak, mdd = start_equity, 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    tr = sorted((r["net_pnl"] for r in rows if r["kind"] == "TRANCHE"), reverse=True)
    gw = sum(x for x in tr if x > 0)
    gl = -sum(x for x in tr if x <= 0)
    net = vals[-1] - start_equity
    return {"final_equity": vals[-1], "net_pnl": net, "return_pct": 100 * (vals[-1] / start_equity - 1),
            "sharpe": (mu / sd * math.sqrt(365)) if sd > 0 else 0.0, "max_drawdown_pct": 100 * mdd,
            "trades": len(tr), "rows": len(rows), "ledger_sum_net_pnl": sum(r["net_pnl"] for r in rows),
            "ladder_pnl": sum(tr),
            "profit_factor": (gw / gl) if gl > 0 else (math.inf if gw > 0 else 0.0),
            "win_rate_pct": 100 * sum(1 for x in tr if x > 0) / len(tr) if tr else 0.0,
            "net_without_top3": net - sum(tr[:3]),
            "fees": sum(r["fees"] for r in rows)}


def span(period):
    return tuple(date.fromisoformat(x) for x in PERIODS[period])


def evaluate(market):
    dds = {s: drawdown_series(market[s]) for s in SYMBOLS}
    res = {"strategy": {}, "buy_hold": {}, "neighbors_validation_x2": {}, "walk_forward_x2": {},
           "info_validation_x1": {}}
    ledger, val_curve = [], None

    def run(s, e, mult, tag, **kw):
        rows, cv = simulate(market, dds, s, e, mult, **kw)
        ledger.extend({**tag, **r} for r in rows)
        return metrics(cv, rows), cv

    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            bh = metrics(buy_hold_basket(market, s, e, mult), [])
            res["buy_hold"][f"{period}/x{mult}"] = bh
            m, cv = run(s, e, mult, {"variant": "L20_30_40", "period": period, "cost_multiplier": mult})
            m["excess_vs_bh_pnl"] = m["net_pnl"] - bh["net_pnl"]
            res["strategy"][f"{period}/x{mult}"] = m
            if period == "validation" and mult == 1:
                val_curve = cv
    s, e = span("validation")
    for name, lv in NEIGHBORS.items():
        m, _ = run(s, e, 2, {"variant": name, "period": "validation", "cost_multiplier": 2}, levels=lv)
        res["neighbors_validation_x2"][name] = m
    for y in WF_YEARS:
        ys, ye = date(y, 1, 1), date(y, 12, 31)
        m, _ = run(ys, ye, 2, {"variant": "L20_30_40", "period": f"wf_{y}", "cost_multiplier": 2})
        m["bh"] = metrics(buy_hold_basket(market, ys, ye, 2), [])
        res["walk_forward_x2"][str(y)] = m
    for period in ("validation", "final_test"):
        ps, pe = span(period)
        m, _ = run(ps, pe, 1, {"variant": "STATIC_50_50", "period": period, "cost_multiplier": 1}, ladder=False)
        res["info_validation_x1"][f"static_50_50/{period}"] = m
    m, _ = run(s, e, 1, {"variant": "BTC_ONLY", "period": "validation", "cost_multiplier": 1}, symbols=("BTCUSDT",))
    res["info_validation_x1"]["BTC_sleeve_only"] = m
    res["info_validation_x1"]["BH_BTC"] = metrics(buy_hold_basket(market, s, e, 1, symbols=("BTCUSDT",)), [])

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    res["dsr_validation_x1"] = dsr_from_returns(daily_returns(val_curve, START_EQUITY), DSR_N, DSR_VAR_ANNUAL / 365)
    res["verdict"] = verdict(res)
    return res, ledger


def verdict(res):
    g = lambda p, m: res["strategy"][f"{p}/x{m}"]
    bh = lambda p, m: res["buy_hold"][f"{p}/x{m}"]
    v1, v2, f1, f2, t1 = g("validation", 1), g("validation", 2), g("final_test", 1), g("final_test", 2), g("tuning", 1)
    a = {"A1_validation_sharpe_and_dd_beat_bh_x1": v1["sharpe"] > bh("validation", 1)["sharpe"]
         and v1["max_drawdown_pct"] < bh("validation", 1)["max_drawdown_pct"],
         "A2_validation_trades_ge_30": v1["trades"] >= 30,
         "A3_validation_x2_pf_gt_1_2_and_net_gt_0": v2["profit_factor"] > 1.2 and v2["net_pnl"] > 0,
         "A4_validation_x1_net_without_top3_gt_0": v1["net_without_top3"] > 0,
         "A5_final_x2_net_gt_0_sharpe_and_dd_beat_bh": f2["net_pnl"] > 0 and f2["sharpe"] > bh("final_test", 2)["sharpe"]
         and f2["max_drawdown_pct"] < bh("final_test", 2)["max_drawdown_pct"]}
    b = {"B1_val_x2_profit_pf": v2["net_pnl"] > 0 and v2["profit_factor"] > 1.2,
         "B2_dd_le_0_6_bh": v1["max_drawdown_pct"] <= 0.6 * bh("validation", 1)["max_drawdown_pct"]
         and f1["max_drawdown_pct"] <= 0.6 * bh("final_test", 1)["max_drawdown_pct"],
         "B3_final_x2_profit": f2["net_pnl"] > 0,
         "B4_val_wo_top3": v1["net_without_top3"] > 0,
         "B5_trades_ge_20": v1["trades"] + f1["trades"] >= 20,
         "B6_tuning_x1_profit": t1["net_pnl"] > 0}
    wf_pos = sum(1 for y in res["walk_forward_x2"].values() if y["net_pnl"] > 0)
    robust = {"dsr_ge_0_95": res["dsr_validation_x1"]["dsr"] >= 0.95,
              "neighbors_val_x2_profit": all(m["net_pnl"] > 0 for m in res["neighbors_validation_x2"].values()),
              "walk_forward_ge_3_of_4": wf_pos >= 3}
    pa, pb = all(a.values()), all(b.values())
    status = "KANDIDÁT NA FORWARD PAPER" if (pa or pb) and all(robust.values()) else "ZAMÍTNUTO"
    return {"track_a": a, "track_b": b, "passed_a": pa, "passed_b": pb, "robustness": robust,
            "walk_forward_positive_years": wf_pos, "status": status}


FIELDS = ["variant", "period", "cost_multiplier", "asset", "kind", "level", "entry_day", "exit_day", "dd_entry",
          "start_value", "end_value", "gross_pnl", "fees", "net_pnl"]


def write(outdir, res, ledger, manifest):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (out / "data_source.json").write_text(json.dumps(
        {"source": "https://data.binance.vision spot monthly 1d klines (public, no keys)",
         "archives": manifest}, indent=0) + "\n")
    (out / "RESULTS.md").write_text(report(res))


def report(res):
    v = res["verdict"]
    yn = lambda ok: "ano" if ok else "NE"
    L = ["# Kontrariánský žebřík 20/30/40 %, 8 aktiv — výsledky (protokol `PROTOCOL.md`)", "",
         f"**Verdikt: {v['status']}** — jediná varianta, 8 rukávů po 50 % základ + 50 % žebřík.", "",
         "| kritérium | splněno |", "|---|---|"]
    L += [f"| {k} | {yn(ok)} |" for k, ok in {**v["track_a"], **v["track_b"], **v["robustness"]}.items()]
    L += ["", f"DSR validace ×1 (N = {DSR_N}): {res['dsr_validation_x1']['dsr']:.3f}; walk-forward kladných let: "
          f"{v['walk_forward_positive_years']}/4.", "",
          "## Strategie vs. buy & hold rovnovážného koše 8 aktiv", "",
          "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | tranše | P/L žebříku | PF tranší | bez top 3 | poplatky | B&H výnos % | B&H Sharpe | B&H DD % |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]
            L.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | "
                     f"{g['trades']} | {g['ladder_pnl']:.2f} | {g['profit_factor']:.2f} | {g['net_without_top3']:.2f} | {g['fees']:.2f} | "
                     f"{b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    L += ["", "## Robustnost", "", "| test | čistý P/L | výnos % | Sharpe | DD % | tranše |", "|---|---|---|---|---|---|"]
    for k, g in res["neighbors_validation_x2"].items():
        L.append(f"| soused {k}, validace ×2 | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    for y, g in res["walk_forward_x2"].items():
        L.append(f"| WF {y} ×2 (B&H {g['bh']['return_pct']:.1f} %) | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "## Informačně (×1, NEJSOU kritériem)", "",
          "| varianta | výnos % | Sharpe | DD % | tranše |", "|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
        L.append(f"| {k} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "Pozn.: `trades.csv` řádky BASE (základ rukávu) + TRANCHE (tranše); součet net_pnl bloku = čistý P/L bloku.",
          "", "Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    market, manifest = load(a.cache)
    res, ledger = evaluate(market)
    write(a.outdir, res, ledger, manifest)
    s = {k: res["strategy"][k] for k in ("tuning/x1", "validation/x1", "validation/x2", "final_test/x2")}
    print("SUMMARY", json.dumps({"verdict": res["verdict"], "dsr": res["dsr_validation_x1"]["dsr"], "strategy": s,
                                 "bh": {k: res["buy_hold"][k] for k in s}}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
