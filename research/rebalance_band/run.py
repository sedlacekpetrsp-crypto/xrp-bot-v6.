"""Pásmový rebalance koše BTC/ETH 50/50 (±5 p. b.) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data, bez klíčů a objednávek.

    python -m research.rebalance_band.run --cache /tmp/vision-1d --outdir research/rebalance_band

Loader a metriky převzaty z research/ethbtc_switch/run.py (PR #17), simulace nová:
dvě sleeve (BTC, ETH), vždy plně investováno; při |w_BTC - 0,5| > pásmo (k close) za open dalšího dne
převod přebytku do druhé sleeve na 50/50.
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
BAND = 0.05
INFO_VARIANTS = ("band10", "monthly")
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
SLEEVE = 0.5
START_EQUITY = 10_000.0


# ------------------------------------------------------------------ data (beze změny z PR #17)
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


# ------------------------------------------------------------------ simulace
def should_rebalance(variant, w_prev_close, d, band=BAND):
    """Rozhodnutí pro open dne d z vah k close(d-1)."""
    if variant == "monthly":
        return d.day == 1
    b = {"band5": band, "band10": 0.10}[variant]
    return abs(w_prev_close - 0.5) > b


def simulate(market, start, end, mult, variant="band5", equity=START_EQUITY):
    """Ledger: obchod = úsek držení jedné sleeve. start_value = tržní hodnota sleeve (qty*open) po vstupu/rebalanci
    (první úsek: alokovaná hotovost před náklady); end_value = tržní hodnota při ukončení úseku MINUS náklady
    přiřazené úseku (prodejní strana přebytku k prodávané sleeve, nákupní strana ke kupované; konec = výnos prodeje).
    ⇒ součet net_pnl = konečná hotovost - počáteční kapitál."""
    fee, slip = FEE * mult, SLIP * mult
    k_sell = (1 - slip) * (1 - fee)          # hotovost na 1 USD tržní hodnoty prodané
    k_buy = 1 / ((1 + slip) * (1 + fee))     # tržní hodnota na 1 USD hotovosti
    px = {s: by_day(market[s]) for s in SYMBOLS}
    days = []
    d = start
    while d <= end:
        for s in SYMBOLS:
            if d not in px[s]:
                raise ValueError(f"chybí {s} {d}")
        days.append(d)
        d += timedelta(days=1)
    trades, curve, rebal = [], {}, 0
    qty, seg = {}, {}

    def open_seg(s, d, price, start_value, fees):
        seg[s] = {"symbol": s, "entry_day": d.isoformat(), "entry_px": price, "start_value": start_value, "fees": fees}

    def close_seg(s, d, price, mark, cost, reason):
        g = seg[s]
        end_value = mark - cost
        fees = g["fees"] + cost
        net = end_value - g["start_value"]
        trades.append({**g, "qty": qty[s], "exit_day": d.isoformat(), "exit_px": price, "exit_reason": reason,
                       "end_value": end_value, "gross_pnl": net + fees, "fees": fees, "net_pnl": net})

    w_prev = None
    for j, d in enumerate(days):
        o = {s: px[s][d]["open"] for s in SYMBOLS}
        c = {s: px[s][d]["close"] for s in SYMBOLS}
        if j == 0:
            for s in SYMBOLS:
                cash = equity * SLEEVE
                qty[s] = cash * k_buy / o[s]
                open_seg(s, d, o[s], cash, cash - qty[s] * o[s])
        elif should_rebalance(variant, w_prev, d):
            v = {s: qty[s] * o[s] for s in SYMBOLS}
            over = max(SYMBOLS, key=lambda s: v[s])
            under = [s for s in SYMBOLS if s != over][0]
            k = k_sell * k_buy
            x = (v[over] - v[under]) / (1 + k)  # tržní hodnota prodaná z přebytku
            c_sell = x * (1 - k_sell)
            c_buy = x * k_sell * (1 - k_buy)
            reason = f"rebalance w_BTC={w_prev:.3f}"
            close_seg(over, d, o[over], v[over], c_sell, reason)
            close_seg(under, d, o[under], v[under], c_buy, reason)
            qty[over] -= x / o[over]
            qty[under] += x * k / o[under]
            for s in SYMBOLS:
                open_seg(s, d, o[s], qty[s] * o[s], 0.0)
            rebal += 1
        vc = {s: qty[s] * c[s] for s in SYMBOLS}
        w_prev = vc["BTCUSDT"] / (vc["BTCUSDT"] + vc["ETHUSDT"])
        if j == len(days) - 1:
            total = 0.0
            for s in SYMBOLS:
                close_seg(s, d, c[s], vc[s], vc[s] * (1 - k_sell), "period_end")
                total += vc[s] * k_sell
            curve[d] = total
        else:
            curve[d] = vc["BTCUSDT"] + vc["ETHUSDT"]
    return trades, curve, rebal


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


# ------------------------------------------------------------------ metriky (beze změny z PR #17)
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
    out = {"basket_50_50": metrics(combine([buy_hold(market[x], s, e, mult) for x in SYMBOLS]), [], START_EQUITY)}
    for sym in SYMBOLS:
        out[f"{sym[:3]}_only"] = metrics(buy_hold(market[sym], s, e, mult, START_EQUITY), [], START_EQUITY)
    return out


def evaluate(market):
    res = {"strategy": {}, "buy_hold": {}, "rebalances": {}, "info_validation_x1": {}}
    ledger = []
    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            res["buy_hold"][f"{period}/x{mult}"] = run_bh(market, period, mult)
            tr, cv, nr = simulate(market, s, e, mult)
            m = metrics(cv, tr, START_EQUITY)
            bh = res["buy_hold"][f"{period}/x{mult}"]["basket_50_50"]
            m["excess_vs_bh_pnl"] = m["net_pnl"] - bh["net_pnl"]
            res["strategy"][f"{period}/x{mult}"] = m
            res["rebalances"][f"{period}/x{mult}"] = nr
            ledger += [{"variant": "band5", "period": period, "cost_multiplier": mult, **t} for t in tr]
    s, e = span("validation")
    for v in INFO_VARIANTS:  # jen informace
        tr, cv, nr = simulate(market, s, e, 1, v)
        m = metrics(cv, tr, START_EQUITY)
        m["rebalances"] = nr
        res["info_validation_x1"][v] = m
        ledger += [{"variant": v, "period": "validation", "cost_multiplier": 1, **t} for t in tr]
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
    lines = ["# Pásmový rebalance BTC/ETH 50/50 ±5 p. b. — výsledky (protokol `PROTOCOL.md`)", "",
             f"**Verdikt: {v['status']}** — jediná předem daná varianta (pásmo ±5 p. b., rebalance za open dalšího dne).", "",
             "| kritérium | splněno |", "|---|---|"]
    lines += [f"| {k} | {'ano' if ok else 'NE'} |" for k, ok in v["checks"].items()]
    lines += ["", "## Strategie vs. buy & hold koše BTC/ETH 50/50 (bez rebalance)", "",
              "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | rebal. | PF | bez top 3 | rozdíl vs B&H | B&H výnos % | B&H Sharpe | B&H max DD % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]["basket_50_50"]
            lines.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | "
                         f"{g['max_drawdown_pct']:.1f} | {g['trades']} | {res['rebalances'][f'{p}/x{m}']} | {g['profit_factor']:.2f} | "
                         f"{g['net_without_top3']:.2f} | {g['excess_vs_bh_pnl']:.2f} | {b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    lines += ["", "## Informačně: B&H jednotlivých aktiv (×1)", "", "| období | BTC výnos % | BTC Sharpe | BTC DD % | ETH výnos % | ETH Sharpe | ETH DD % |",
              "|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        b = res["buy_hold"][f"{p}/x1"]
        lines.append(f"| {p} | {b['BTC_only']['return_pct']:.1f} | {b['BTC_only']['sharpe']:.2f} | {b['BTC_only']['max_drawdown_pct']:.1f} | "
                     f"{b['ETH_only']['return_pct']:.1f} | {b['ETH_only']['sharpe']:.2f} | {b['ETH_only']['max_drawdown_pct']:.1f} |")
    lines += ["", "## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)", "",
              "| varianta | čistý P/L | Sharpe | max DD % | obchody | rebal. | PF |", "|---|---|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
        lines.append(f"| {k} | {g['net_pnl']:.2f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} | {g['rebalances']} | {g['profit_factor']:.2f} |")
    lines += ["", "Pozn.: „obchod“ = úsek držení jedné sleeve; při kladném trhu jsou úseky většinou ziskové bez ohledu na hranu,",
              "proto rozhoduje hlavně srovnání s B&H (krit. 1 a 5) a sloupec „rozdíl vs B&H“.", "",
              "Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.", ""]
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
