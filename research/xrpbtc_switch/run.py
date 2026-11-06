"""Přepínání BTC <-> XRP podle trendu XRPBTC (SMA50) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data, bez klíčů a objednávek.

    python -m research.xrpbtc_switch.run --cache /tmp/vision-1d --outdir research/xrpbtc_switch

Loader a metriky převzaty z research/ts_momentum_vote/run.py (PR #16), simulace nová:
vždy 100 % v jednom aktivu (BTC nebo XRP), přepnutí za open dne po signálu.
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

SYMBOLS = ("BTCUSDT", "XRPUSDT", "XRPBTC")
ASSET = {"BTC": "BTCUSDT", "XRP": "XRPUSDT"}
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
SMA_N = 50
INFO_SMA = (20, 100)
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
def by_day(bars):
    return {day(b["ts"]): b for b in bars}


def target(xrpbtc_close, t, n=SMA_N):
    """XRP, pokud close XRPBTC(t) > SMA_n(t) (posledních n close včetně t), jinak BTC. Chybějící den = ValueError."""
    closes = []
    for k in range(n):
        d = t - timedelta(days=k)
        if d not in xrpbtc_close:
            raise ValueError(f"chybí XRPBTC close {d}")
        closes.append(xrpbtc_close[d])
    return "XRP" if closes[0] > sum(closes) / n else "BTC"


def simulate(market, start, end, mult, n=SMA_N, equity=START_EQUITY):
    """Vždy plně v jednom aktivu. Signál z close(d-1), obchod za open(d): prodej open*(1-skluz) - poplatek,
    nákup open*(1+skluz) + poplatek. Konec období = prodej za close*(1-skluz) - poplatek.
    Obchod = jedno držení; net_pnl = výnos prodeje po poplatku - utracená hotovost vč. poplatku."""
    fee, slip = FEE * mult, SLIP * mult
    px = {a: by_day(market[s]) for a, s in ASSET.items()}
    ec = {d: b["close"] for d, b in by_day(market["XRPBTC"]).items()}
    days = []
    d = start
    while d <= end:
        for a in ASSET:
            if d not in px[a]:
                raise ValueError(f"chybí {a} {d}")
        days.append(d)
        d += timedelta(days=1)
    trades, curve = [], {}
    cash, held, qty, pos = equity, None, 0.0, None

    def buy(a, d, price):
        nonlocal cash, held, qty, pos
        p = price * (1 + slip)
        q = cash / (p * (1 + fee))
        f = q * p * fee
        pos = {"symbol": ASSET[a], "entry_day": d.isoformat(), "entry_px": p, "qty": q,
               "start_value": cash, "fees": f}
        cash, held, qty = 0.0, a, q

    def sell(d, price, reason):
        nonlocal cash, held, qty, pos
        p = price * (1 - slip)
        proceeds = qty * p
        f = proceeds * fee
        cash = proceeds - f
        net = cash - pos["start_value"]
        fees = pos["fees"] + f
        trades.append({**pos, "exit_day": d.isoformat(), "exit_px": p, "exit_reason": reason,
                       "end_value": cash, "gross_pnl": net + fees, "fees": fees, "net_pnl": net})
        held, qty, pos = None, 0.0, None  # nulovat i zbytkovou qty

    for j, d in enumerate(days):
        tgt = target(ec, d - timedelta(days=1), n)
        if held is None:
            buy(tgt, d, px[tgt][d]["open"])
        elif tgt != held:
            sell(d, px[held][d]["open"], f"switch {held}->{tgt}")
            buy(tgt, d, px[tgt][d]["open"])
        if j == len(days) - 1:
            sell(d, px[held][d]["close"], "period_end")
            curve[d] = cash
        else:
            curve[d] = qty * px[held][d]["close"]
    return trades, curve


def buy_hold(bars, start, end, mult, equity=START_EQUITY * SLEEVE):
    fee, slip = FEE * mult, SLIP * mult
    sel = [b for b in bars if start <= day(b["ts"]) <= end]
    p = sel[0]["open"] * (1 + slip)
    q = equity / (p * (1 + fee))
    curve = {}
    for j, b in enumerate(sel):
        v = q * b["close"]
        if j == len(sel) - 1:
            v *= (1 - slip) * (1 - fee)
        curve[day(b["ts"])] = v
    return curve


# ------------------------------------------------------------------ metriky (beze změny z PR #15)
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


def span(period):
    return tuple(date.fromisoformat(x) for x in PERIODS[period])


def run_bh(market, period, mult):
    s, e = span(period)
    out = {"basket_50_50": metrics(combine([buy_hold(market[x], s, e, mult) for x in ("BTCUSDT", "XRPUSDT")]),
                                   [], START_EQUITY)}
    for a, sym in ASSET.items():
        out[f"{a}_only"] = metrics(buy_hold(market[sym], s, e, mult, START_EQUITY), [], START_EQUITY)
    return out


def xrp_share(trades):
    tot = sum((date.fromisoformat(t["exit_day"]) - date.fromisoformat(t["entry_day"])).days for t in trades)
    xrp = sum((date.fromisoformat(t["exit_day"]) - date.fromisoformat(t["entry_day"])).days
              for t in trades if t["symbol"] == "XRPUSDT")
    return 100 * xrp / tot if tot else 0.0


def evaluate(market):
    res = {"strategy": {}, "buy_hold": {}, "xrp_time_share_pct": {}, "info_validation_x1": {}}
    ledger = []
    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            res["buy_hold"][f"{period}/x{mult}"] = run_bh(market, period, mult)
            tr, cv = simulate(market, s, e, mult)
            res["strategy"][f"{period}/x{mult}"] = metrics(cv, tr, START_EQUITY)
            if mult == 1:
                res["xrp_time_share_pct"][period] = xrp_share(tr)
            ledger += [{"variant": f"SMA{SMA_N}", "period": period, "cost_multiplier": mult, **t} for t in tr]
    s, e = span("validation")
    for n in INFO_SMA:  # jen informace
        tr, cv = simulate(market, s, e, 1, n)
        res["info_validation_x1"][f"SMA{n}"] = metrics(cv, tr, START_EQUITY)
        ledger += [{"variant": f"SMA{n}", "period": "validation", "cost_multiplier": 1, **t} for t in tr]
    res["verdict"] = verdict(res)
    return res, ledger


def verdict(res):
    g = lambda p, m: res["strategy"][f"{p}/x{m}"]
    bh = lambda p, m: res["buy_hold"][f"{p}/x{m}"]["basket_50_50"]
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


FIELDS = ["variant", "period", "cost_multiplier", "symbol", "entry_day", "exit_day", "exit_reason",
          "entry_px", "exit_px", "qty", "start_value", "end_value", "gross_pnl", "fees", "net_pnl"]


def write(outdir, res, ledger, manifest):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(ledger)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (out / "data_source.json").write_text(json.dumps(
        {"source": "https://data.binance.vision spot monthly 1d klines (public, no keys)",
         "archives": manifest}, indent=0) + "\n")
    (out / "RESULTS.md").write_text(report(res))


def report(res):
    v = res["verdict"]
    lines = ["# Přepínání BTC ↔ XRP podle trendu XRPBTC — výsledky (protokol `PROTOCOL.md`)", "",
             f"**Verdikt: {v['status']}** — jediná předem daná varianta (XRPBTC close > SMA50 ⇒ XRP, jinak BTC; vždy investováno).", "",
             "| kritérium | splněno |", "|---|---|"]
    lines += [f"| {k} | {'ano' if ok else 'NE'} |" for k, ok in v["checks"].items()]
    lines += ["", "## Strategie vs. buy & hold koše BTC/XRP 50/50", "",
              "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]["basket_50_50"]
            lines.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | "
                         f"{g['max_drawdown_pct']:.1f} | {g['trades']} | {g['profit_factor']:.2f} | {g['win_rate_pct']:.0f} | "
                         f"{g['net_without_top3']:.2f} | {g['avg_hold_days']:.1f} | {b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    lines += ["", "## Informačně: B&H jednotlivých aktiv (×1)", "", "| období | BTC výnos % | BTC Sharpe | BTC DD % | XRP výnos % | XRP Sharpe | XRP DD % |",
              "|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        b = res["buy_hold"][f"{p}/x1"]
        lines.append(f"| {p} | {b['BTC_only']['return_pct']:.1f} | {b['BTC_only']['sharpe']:.2f} | {b['BTC_only']['max_drawdown_pct']:.1f} | "
                     f"{b['XRP_only']['return_pct']:.1f} | {b['XRP_only']['sharpe']:.2f} | {b['XRP_only']['max_drawdown_pct']:.1f} |")
    lines += ["", "Podíl času v XRP (×1): " + ", ".join(f"{p} {x:.0f} %" for p, x in res["xrp_time_share_pct"].items()), "",
              "## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)", "",
              "| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |", "|---|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
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
    print(json.dumps({"verdict": res["verdict"], "trades_in_ledger": len(ledger)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
