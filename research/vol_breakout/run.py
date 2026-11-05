"""Denní volatilitní průraz (open + k × včerejší rozpětí, výstup na close dne) BTC/ETH — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data, bez klíčů a objednávek.

    python -m research.vol_breakout.run --cache /tmp/vision-1d --outdir research/vol_breakout
"""
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SYMBOLS = ("BTCUSDT", "ETHUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
K = 0.5
INFO_VARIANTS = {"k03": {"k": 0.3}, "k07": {"k": 0.7}, "k05_sma200": {"k": 0.5, "sma_filter": 200}}
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
SLEEVE = 0.5
START_EQUITY = 10_000.0


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


# ------------------------------------------------------------------ pravidla
def sma(closes, n):
    out, acc = [None] * len(closes), 0.0
    for i, c in enumerate(closes):
        acc += c
        if i >= n:
            acc -= closes[i - n]
        if i >= n - 1:
            out[i] = acc / n
    return out


def simulate(bars, start, end, mult, symbol="X", k=K, sma_filter=None, equity=START_EQUITY * SLEEVE):
    """Jedna sleeve. Den t: T = open(t) + k*(high(t-1)-low(t-1)); high(t) >= T => nákup za max(open,T)+skluz,
    prodej za close(t)-skluz. Žádné držení přes noc. Volitelný filtr close(t-1) > SMA(n)(t-1)."""
    fee, slip = FEE * mult, SLIP * mult
    closes = [b["close"] for b in bars]
    s = sma(closes, sma_filter) if sma_filter else None
    trades, curve, cash = [], {}, equity
    for i, bar in enumerate(bars):
        d = day(bar["ts"])
        if not (start <= d <= end):
            continue
        if i > 0:
            prev = bars[i - 1]
            trig = bar["open"] + k * (prev["high"] - prev["low"])
            ok = s is None or (s[i - 1] is not None and prev["close"] > s[i - 1])
            if ok and bar["high"] >= trig:
                px = max(bar["open"], trig) * (1 + slip)
                qty = cash / (px * (1 + fee))
                efee = qty * px * fee
                cash -= qty * px + efee
                pos = {"entry_day": d, "entry_px": px, "qty": qty, "entry_fee": efee}
                cash += close_pos(trades, pos, bar["close"] * (1 - slip), fee, d, symbol, "day_close")
        curve[d] = cash
    return trades, curve


def close_pos(trades, pos, px, fee, d, symbol, reason):
    proceeds = pos["qty"] * px
    xfee = proceeds * fee
    gross = (px - pos["entry_px"]) * pos["qty"]
    trades.append({"symbol": symbol, "entry_day": pos["entry_day"].isoformat(), "exit_day": d.isoformat(),
                   "exit_reason": reason, "entry_px": pos["entry_px"], "exit_px": px, "qty": pos["qty"],
                   "gross_pnl": gross, "fees": pos["entry_fee"] + xfee,
                   "net_pnl": gross - pos["entry_fee"] - xfee})
    return proceeds - xfee


def buy_hold(bars, start, end, mult, equity=START_EQUITY * SLEEVE):
    fee, slip = FEE * mult, SLIP * mult
    sel = [b for b in bars if start <= day(b["ts"]) <= end]
    px = sel[0]["open"] * (1 + slip)
    qty = equity / (px * (1 + fee))
    curve = {}
    for j, b in enumerate(sel):
        v = qty * b["close"]
        if j == len(sel) - 1:
            v *= (1 - slip) * (1 - fee)
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
            "net_without_top3": sum(nets[3:]) if len(nets) > 3 else 0.0,
            "fees": sum(t["fees"] for t in trades),
            "avg_hold_days": (sum((date.fromisoformat(t["exit_day"]) - date.fromisoformat(t["entry_day"])).days
                                  for t in trades) / len(trades)) if trades else 0.0}


def run_variant(market, period, mult, **kw):
    s, e = (date.fromisoformat(x) for x in PERIODS[period])
    all_trades, curves, per_symbol = [], [], {}
    for sym in SYMBOLS:
        tr, cv = simulate(market[sym], s, e, mult, sym, **kw)
        all_trades += tr
        curves.append(cv)
        per_symbol[sym] = metrics(cv, tr, START_EQUITY * SLEEVE)
        held = sum((date.fromisoformat(t["exit_day"]) - date.fromisoformat(t["entry_day"])).days + 1 for t in tr)
        per_symbol[sym]["exposure_pct"] = 100 * held / max(len(cv), 1)
    return metrics(combine(curves), all_trades, START_EQUITY), per_symbol, all_trades


def run_bh(market, period, mult):
    s, e = (date.fromisoformat(x) for x in PERIODS[period])
    curves = [buy_hold(market[sym], s, e, mult) for sym in SYMBOLS]
    return metrics(combine(curves), [], START_EQUITY)


def evaluate(market):
    res = {"strategy": {}, "buy_hold": {}, "per_symbol": {}, "info_validation_x1": {}}
    ledger = []
    for period in PERIODS:
        for mult in COST_MULTIPLIERS:
            res["buy_hold"][f"{period}/x{mult}"] = run_bh(market, period, mult)
            b, ps, tr = run_variant(market, period, mult)
            res["strategy"][f"{period}/x{mult}"] = b
            res["per_symbol"][f"{period}/x{mult}"] = ps
            ledger += [{"variant": "K05", "period": period, "cost_multiplier": mult, **t} for t in tr]
    for name, kw in INFO_VARIANTS.items():  # jen informace
        b, _, tr = run_variant(market, "validation", 1, **kw)
        res["info_validation_x1"][name] = b
        ledger += [{"variant": name, "period": "validation", "cost_multiplier": 1, **t} for t in tr]
    v1 = res["strategy"]["validation/x1"]
    s, e = (date.fromisoformat(x) for x in PERIODS["validation"])
    ndays = sum(1 for sym in SYMBOLS for b in market[sym] if s <= day(b["ts"]) <= e)
    res["info_validation_x1"]["trade_day_share_pct"] = {"value": 100 * v1["trades"] / ndays}
    vt = [t for t in ledger if t["variant"] == "K05" and t["period"] == "validation" and t["cost_multiplier"] == 1]
    res["info_validation_x1"]["avg_net_bps_per_trade"] = {
        "value": 1e4 * sum(t["net_pnl"] / (t["qty"] * t["entry_px"]) for t in vt) / len(vt) if vt else 0.0}
    res["verdict"] = verdict(res)
    return res, ledger


def verdict(res):
    g = lambda p, m: res["strategy"][f"{p}/x{m}"]
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
    return {"checks": checks, "status": "KANDIDÁT NA FORWARD PAPER" if all(checks.values()) else "ZAMÍTNUTO"}


def write(outdir, res, ledger, manifest):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    fields = ["variant", "period", "cost_multiplier", "symbol", "entry_day", "exit_day", "exit_reason", "entry_px",
              "exit_px", "qty", "gross_pnl", "fees", "net_pnl"]
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
    lines = ["# Denní volatilitní průraz k=0,5 BTC/ETH — výsledky (protokol `PROTOCOL.md`)", "",
             f"**Verdikt: {v['status']}** — jediná předem daná varianta (vstup open + 0,5 × včerejší rozpětí, výstup close téhož dne).", "",
             "| kritérium | splněno |", "|---|---|"]
    lines += [f"| {k} | {'ano' if ok else 'NE'} |" for k, ok in v["checks"].items()]
    lines += ["", "## Strategie vs. buy & hold (koš 2 × 50 %)", "",
              "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]
            lines.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | "
                         f"{g['max_drawdown_pct']:.1f} | {g['trades']} | {g['profit_factor']:.2f} | {g['win_rate_pct']:.0f} | "
                         f"{g['net_without_top3']:.2f} | {g['avg_hold_days']:.1f} | {b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    lines += ["", "## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)", "",
              "| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |", "|---|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
        if "value" in g:
            lines.append(f"| {k} | {g['value']:.2f} | | | | |")
            continue
        lines.append(f"| {k} | {g['net_pnl']:.2f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} | {g['profit_factor']:.2f} |")
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
    print(json.dumps({"verdict": res["verdict"],
                      "trades_in_ledger": len(ledger)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
