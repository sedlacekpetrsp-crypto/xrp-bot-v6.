"""Donchian trend 20/55 — backtest podle PROTOCOL.md (PAPER výzkum, veřejná data, bez klíčů a objednávek).

    python -m research.donchian_trend.run --cache /tmp/vision-1d --outdir research/donchian_trend
"""
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
FIRST_MONTH = {"BTCUSDT": (2020, 1), "ETHUSDT": (2020, 1), "XRPUSDT": (2020, 1), "SOLUSDT": (2020, 8)}
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
GRID = [(20, 2.0), (20, 3.0), (55, 2.0), (55, 3.0)]
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
SLEEVE = 0.25
START_EQUITY = 10_000.0
DAY_MS = 86_400_000


# ------------------------------------------------------------------ data
def months(symbol):
    y, m = FIRST_MONTH[symbol]
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
            continue  # případná hlavička
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
        for y, m in months(s):
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
        bars.sort(key=lambda x: x["ts"])
        dedup = {b["ts"]: b for b in bars}
        market[s] = [dedup[t] for t in sorted(dedup)]
    return market, manifest


# ------------------------------------------------------------------ pravidla
def day(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).date()


def atr_series(bars, n=20):
    """Wilder ATR: první hodnota = průměr TR prvních n dnů, dál rekurzivně. Jen minulá a dnešní data."""
    out, atr = [], None
    for i in range(len(bars)):
        tr = _tr(bars, i)
        if i < n - 1:
            out.append(None)
            continue
        atr = sum(_tr(bars, j) for j in range(n)) / n if i == n - 1 else (atr * (n - 1) + tr) / n
        out.append(atr)
    return out


def _tr(bars, j):
    b = bars[j]
    if j == 0:
        return b["high"] - b["low"]
    pc = bars[j - 1]["close"]
    return max(b["high"] - b["low"], abs(b["high"] - pc), abs(b["low"] - pc))


def simulate(bars, start, end, n, k, mult, symbol="X", equity=START_EQUITY * SLEEVE):
    """Jedna sleeve. start/end = date (včetně). Vrací (obchody, denní equity {date: hodnota})."""
    fee, slip = FEE * mult, SLIP * mult
    m = n // 2
    atr = atr_series(bars)
    trades, curve = [], {}
    pos = None  # dict(entry_px, qty, stop, entry_day, entry_cost)
    sig_atr = None
    pending = None  # "buy" / "sell" na open dalšího dne
    cash = equity
    idx = [i for i, b in enumerate(bars) if start <= day(b["ts"]) <= end]
    if not idx:
        return trades, curve
    for i in idx:
        b = bars[i]
        d = day(b["ts"])
        # 1) provedení příkazů na open
        if pending == "buy" and pos is None:
            px = b["open"] * (1 + slip)
            qty = cash / (px * (1 + fee))
            cost = qty * px * fee
            pos = {"entry_px": px, "qty": qty, "stop": px - k * sig_atr, "entry_day": d,
                   "entry_fee": cost, "entry_open": b["open"]}
            cash -= qty * px + cost
        elif pending == "sell" and pos is not None:
            cash += _close(pos, b["open"] * (1 - slip), fee, d, "CHANNEL_EXIT", trades, symbol)
            pos = None
        pending = None
        # 2) intradenní stop
        if pos is not None and b["low"] <= pos["stop"]:
            px = min(b["open"], pos["stop"]) * (1 - slip)
            cash += _close(pos, px, fee, d, "STOP", trades, symbol)
            pos = None
        # 3) signály na close (jen z minulých dat)
        if i >= n:
            hh = max(x["high"] for x in bars[i - n:i])
            ll = min(x["low"] for x in bars[i - m:i])
            if pos is None and b["close"] > hh and atr[i] is not None:
                pending, sig_atr = "buy", atr[i]
            elif pos is not None and b["close"] < ll:
                pending = "sell"
        # 4) konec období: zavřít za close
        if i == idx[-1] and pos is not None:
            cash += _close(pos, b["close"] * (1 - slip), fee, d, "END_OF_PERIOD", trades, symbol)
            pos = None
        curve[d] = cash + (pos["qty"] * b["close"] if pos else 0.0)
    return trades, curve


def _close(pos, px, fee, d, reason, trades, symbol):
    proceeds = pos["qty"] * px
    exit_fee = proceeds * fee
    gross = (px - pos["entry_px"]) * pos["qty"]
    net = gross - pos["entry_fee"] - exit_fee
    trades.append({"symbol": symbol, "entry_day": pos["entry_day"].isoformat(), "exit_day": d.isoformat(),
                   "entry_px": pos["entry_px"], "exit_px": px, "qty": pos["qty"], "stop": pos["stop"],
                   "reason": reason, "gross_pnl": gross, "fees": pos["entry_fee"] + exit_fee, "net_pnl": net})
    return proceeds - exit_fee


def buy_hold(bars, start, end, mult, symbol="X", equity=START_EQUITY * SLEEVE):
    fee, slip = FEE * mult, SLIP * mult
    sel = [b for b in bars if start <= day(b["ts"]) <= end]
    if not sel:
        return {}
    px = sel[0]["open"] * (1 + slip)
    qty = equity / (px * (1 + fee))
    curve = {}
    for j, b in enumerate(sel):
        v = qty * b["close"]
        if j == len(sel) - 1:
            v = qty * b["close"] * (1 - slip) * (1 - fee)
        curve[day(b["ts"])] = v
    return curve


# ------------------------------------------------------------------ metriky
def combine(curves):
    days = sorted(set().union(*[c.keys() for c in curves]))
    out, last = {}, [None] * len(curves)
    for d in days:
        for j, c in enumerate(curves):
            if d in c:
                last[j] = c[d]
        out[d] = sum(v if v is not None else START_EQUITY * SLEEVE for v in last)
    return out


def metrics(curve, trades, start_equity):
    vals = [curve[d] for d in sorted(curve)]
    rets = [vals[0] / start_equity - 1] + [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    peak, mdd = start_equity, 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    nets = sorted((t["net_pnl"] for t in trades), reverse=True)
    gw = sum(x for x in nets if x > 0)
    gl = -sum(x for x in nets if x <= 0)
    return {"final_equity": vals[-1], "net_pnl": vals[-1] - start_equity,
            "return_pct": 100 * (vals[-1] / start_equity - 1),
            "sharpe": (mu / sd * math.sqrt(365)) if sd > 0 else 0.0,
            "max_drawdown_pct": 100 * mdd, "trades": len(trades),
            "profit_factor": (gw / gl) if gl > 0 else (math.inf if gw > 0 else 0.0),
            "win_rate_pct": 100 * sum(1 for x in nets if x > 0) / len(nets) if nets else 0.0,
            "net_without_top3": sum(nets[3:]) if len(nets) > 3 else 0.0 if nets else 0.0,
            "fees": sum(t["fees"] for t in trades)}


def run_variant(market, period, n, k, mult):
    s, e = (date.fromisoformat(x) for x in PERIODS[period])
    all_trades, curves, per_symbol = [], [], {}
    for sym in SYMBOLS:
        tr, cv = simulate(market[sym], s, e, n, k, mult, sym)
        all_trades += tr
        curves.append(cv)
        per_symbol[sym] = metrics(cv, tr, START_EQUITY * SLEEVE) if cv else None
    basket = metrics(combine(curves), all_trades, START_EQUITY)
    return basket, per_symbol, all_trades


def run_bh(market, period, mult):
    s, e = (date.fromisoformat(x) for x in PERIODS[period])
    curves = [buy_hold(market[sym], s, e, mult, sym) for sym in SYMBOLS]
    return metrics(combine(curves), [], START_EQUITY), {
        sym: metrics(c, [], START_EQUITY * SLEEVE) for sym, c in zip(SYMBOLS, curves) if c}


def evaluate(market):
    res = {"grid": {}, "buy_hold": {}, "per_symbol": {}}
    ledger = []
    for period in PERIODS:
        for mult in COST_MULTIPLIERS:
            res["buy_hold"][f"{period}/x{mult}"] = run_bh(market, period, mult)[0]
    # 1) ladění: výběr jediné varianty
    tuning = {}
    for n, k in GRID:
        b, ps, tr = run_variant(market, "tuning", n, k, 1)
        tuning[f"N{n}_k{k:g}"] = b
    chosen = max(tuning, key=lambda key: tuning[key]["sharpe"])
    res["tuning_selection"] = {"by": "basket sharpe, tuning, cost x1", "scores":
                               {k: v["sharpe"] for k, v in tuning.items()}, "chosen": chosen}
    # 2) všechny varianty všech období (jen pro úplnost evidence; rozhoduje zvolená)
    for n, k in GRID:
        key = f"N{n}_k{k:g}"
        for period in PERIODS:
            for mult in COST_MULTIPLIERS:
                b, ps, tr = run_variant(market, period, n, k, mult)
                res["grid"][f"{key}/{period}/x{mult}"] = b
                if key == chosen:
                    res["per_symbol"][f"{period}/x{mult}"] = ps
                for t in tr:
                    ledger.append({"variant": key, "period": period, "cost_multiplier": mult, **t})
    res["verdict"] = verdict(res, chosen)
    return res, ledger


def verdict(res, chosen):
    g = lambda p, m: res["grid"][f"{chosen}/{p}/x{m}"]
    bh = lambda p, m: res["buy_hold"][f"{p}/x{m}"]
    v1, v2, f2 = g("validation", 1), g("validation", 2), g("final_test", 2)
    checks = {
        "1_validation_sharpe_and_dd_beat_bh_x1": v1["sharpe"] > bh("validation", 1)["sharpe"]
        and v1["max_drawdown_pct"] < bh("validation", 1)["max_drawdown_pct"],
        "2_validation_trades_ge_30": v1["trades"] >= 30,
        "3_validation_x2_pf_gt_1_2_and_net_gt_0": v2["profit_factor"] > 1.2 and v2["net_pnl"] > 0,
        "4_validation_x1_net_without_top3_gt_0": v1["net_without_top3"] > 0,
        "5_final_x2_net_gt_0_sharpe_and_dd_beat_bh": f2["net_pnl"] > 0
        and f2["sharpe"] > bh("final_test", 2)["sharpe"]
        and f2["max_drawdown_pct"] < bh("final_test", 2)["max_drawdown_pct"],
    }
    return {"chosen": chosen, "checks": checks,
            "status": "KANDIDÁT NA FORWARD PAPER" if all(checks.values()) else "ZAMÍTNUTO"}


def write(outdir, res, ledger, manifest):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    fields = ["variant", "period", "cost_multiplier", "symbol", "entry_day", "exit_day", "entry_px",
              "exit_px", "qty", "stop", "reason", "gross_pnl", "fees", "net_pnl"]
    with (out / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(ledger)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (out / "data_source.json").write_text(json.dumps(
        {"source": "https://data.binance.vision spot monthly 1d klines (public, no keys)",
         "archives": manifest}, indent=0) + "\n")
    (out / "RESULTS.md").write_text(report(res))


def report(res):
    v = res["verdict"]
    c = v["chosen"]
    lines = [f"# Donchian trend — výsledky (protokol `PROTOCOL.md`)", "",
             f"**Verdikt: {v['status']}** — zvolená varianta `{c}` (výběr podle Sharpe koše na ladění, náklady ×1).", "",
             "| kritérium | splněno |", "|---|---|"]
    lines += [f"| {k} | {'ano' if ok else 'NE'} |" for k, ok in v["checks"].items()]
    lines += ["", "## Zvolená varianta vs. buy & hold (koš 4 × 25 %)", "",
              "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | bez top 3 | B&H výnos % | B&H Sharpe | B&H max DD % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["grid"][f"{c}/{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]
            lines.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | "
                         f"{g['max_drawdown_pct']:.1f} | {g['trades']} | {g['profit_factor']:.2f} | "
                         f"{g['net_without_top3']:.2f} | {b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    lines += ["", "## Ladění (výběr varianty)", ""]
    lines += [f"- `{k}`: Sharpe {s:.3f}" for k, s in res["tuning_selection"]["scores"].items()]
    lines += ["", "Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    market, manifest = load(a.cache)
    res, ledger = evaluate(market)
    write(a.outdir, res, ledger, manifest)
    print(json.dumps({"verdict": res["verdict"], "trades_in_ledger": len(ledger)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
