"""Mean-reversion poměru ETHBTC (long-only koš BTC/ETH, z20 ±2) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data, bez klíčů a objednávek.

    python -m research.ethbtc_meanrev.run --cache /tmp/vision-1d --outdir research/ethbtc_meanrev

Loader a metriky převzaty z research/rebalance_band/run.py (PR #18), simulace nová:
stavy N (50/50), E (100 % ETH), B (100 % BTC); signál z-skóre ETHBTC k close(t), provedení za open(t+1).
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

SYMBOLS = ("BTCUSDT", "ETHUSDT", "ETHBTC")
ASSETS = ("BTCUSDT", "ETHUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
WINDOW = 20
THRESHOLD = 2.0
INFO_THRESHOLDS = (1.5, 2.5)
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
SLEEVE = 0.5
START_EQUITY = 10_000.0


# ------------------------------------------------------------------ data (beze změny z PR #17/#18)
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
def zscores(ratio_bars, window=WINDOW):
    """z(t) = (close(t) - SMA_w(t)) / populační sd w close, okno včetně t. Jen ze zavřených svíček ≤ t."""
    closes = [(day(b["ts"]), b["close"]) for b in ratio_bars]
    out = {}
    for i in range(window - 1, len(closes)):
        w = [c for _, c in closes[i - window + 1:i + 1]]
        mu = sum(w) / window
        sd = math.sqrt(sum((x - mu) ** 2 for x in w) / window)
        out[closes[i][0]] = (closes[i][1] - mu) / sd if sd > 0 else 0.0
    return out


def next_state(state, z, thr=THRESHOLD):
    if state == "N":
        if z < -thr:
            return "E"
        if z > thr:
            return "B"
    elif state == "E" and z > 0:
        return "N"
    elif state == "B" and z < 0:
        return "N"
    return state


# ------------------------------------------------------------------ simulace
def simulate(market, start, end, mult, thr=THRESHOLD, equity=START_EQUITY):
    """Ledger úseků (segment N/E/B), souvislé: start_value úseku = hodnota portfolia (qty*open) PŘED přechodem,
    kterým úsek začíná (první úsek = počáteční hotovost); end_value = hodnota PO přechodu, kterým končí
    (poslední = výnos likvidace za close). ⇒ součet net_pnl = konečná hotovost - počáteční kapitál.
    Podle protokolu nese epizoda E/B náklady OBOU svých přechodů: vstup N→E/B (start_value epizody = hodnota před
    přechodem) i výstup E/B→N (end_value = hodnota po přechodu). Úsek N nese jen počáteční nákup a případnou likvidaci."""
    fee, slip = FEE * mult, SLIP * mult
    k_sell = (1 - slip) * (1 - fee)
    k_buy = 1 / ((1 + slip) * (1 + fee))
    k = k_sell * k_buy
    px = {s: by_day(market[s]) for s in SYMBOLS}
    z = zscores(market["ETHBTC"])
    days = []
    d = start
    while d <= end:
        for s in SYMBOLS:
            if d not in px[s]:
                raise ValueError(f"chybí {s} {d}")
        if d not in z:
            raise ValueError(f"chybí z-skóre {d}")
        days.append(d)
        d += timedelta(days=1)

    B, E = ASSETS
    qty = {B: 0.0, E: 0.0}
    rows, curve = [], {}
    seg = None
    state = "N"
    pending = None  # stav určený k close(t-1)

    def mark(p):
        return qty[B] * p[B] + qty[E] * p[E]

    def start_seg(st, d, value, reason):
        return {"segment": st, "entry_day": d.isoformat(), "entry_reason": reason, "start_value": value,
                "fees": 0.0, "z_entry": None}

    def end_seg(g, d, value, reason, extra_fees):
        g["fees"] += extra_fees
        net = value - g["start_value"]
        rows.append({**g, "exit_day": d.isoformat(), "exit_reason": reason, "end_value": value,
                     "gross_pnl": net + g["fees"], "net_pnl": net})

    for j, d in enumerate(days):
        o = {s: px[s][d]["open"] for s in ASSETS}
        c = {s: px[s][d]["close"] for s in ASSETS}
        if j == 0:
            seg = start_seg("N", d, equity, "period_start")
            for s in ASSETS:
                cash = equity * SLEEVE
                qty[s] = cash * k_buy / o[s]
            seg["fees"] += equity - mark(o)
        elif pending != state:
            before = mark(o)
            if state == "N":  # N -> E/B: prodat celou druhou nohu, koupit cílovou
                src = B if pending == "E" else E
                dst = E if pending == "E" else B
                x = qty[src] * o[src]
                qty[src] = 0.0
                qty[dst] += x * k / o[dst]
            else:  # E/B -> N: prodat polovinu-ish držené, koupit druhou na 50/50
                src = E if state == "E" else B
                dst = B if state == "E" else E
                x = qty[src] * o[src] / (1 + k)
                qty[src] -= x / o[src]
                qty[dst] += x * k / o[dst]
            after = mark(o)
            reason = f"z={zprev:.3f} {state}->{pending}"
            cost = before - after
            if pending == "N":  # výstup z epizody: náklady nese epizoda
                end_seg(seg, d, after, reason, cost)
                seg = start_seg("N", d, after, reason)
            else:  # vstup do epizody: náklady nese epizoda (start_value = hodnota PŘED přechodem)
                end_seg(seg, d, before, reason, 0.0)
                seg = start_seg(pending, d, before, reason)
                seg["fees"] += cost
            seg["z_entry"] = round(zprev, 4)
            state = pending
        zprev = z[d]
        pending = next_state(state, zprev, thr)
        if j == len(days) - 1:
            vc = mark(c)
            total = vc * k_sell
            end_seg(seg, d, total, "period_end", vc - total)
            curve[d] = total
        else:
            curve[d] = mark(c)
    return rows, curve


def episodes(rows):
    return [r for r in rows if r["segment"] != "N"]


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


# ------------------------------------------------------------------ metriky (beze změny z PR #17/#18)
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
            "episodes_net_pnl": sum(nets),
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
    out = {"basket_50_50": metrics(combine([buy_hold(market[x], s, e, mult) for x in ASSETS]), [], START_EQUITY)}
    for sym in ASSETS:
        out[f"{sym[:3]}_only"] = metrics(buy_hold(market[sym], s, e, mult, START_EQUITY), [], START_EQUITY)
    return out


def evaluate(market):
    res = {"strategy": {}, "buy_hold": {}, "info_validation_x1": {}}
    ledger = []
    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            res["buy_hold"][f"{period}/x{mult}"] = run_bh(market, period, mult)
            rows, cv = simulate(market, s, e, mult)
            m = metrics(cv, episodes(rows), START_EQUITY)
            m["segments_total"] = len(rows)
            m["ledger_sum_net_pnl"] = sum(r["net_pnl"] for r in rows)
            bh = res["buy_hold"][f"{period}/x{mult}"]["basket_50_50"]
            m["excess_vs_bh_pnl"] = m["net_pnl"] - bh["net_pnl"]
            res["strategy"][f"{period}/x{mult}"] = m
            ledger += [{"variant": "z2", "period": period, "cost_multiplier": mult, **r} for r in rows]
    s, e = span("validation")
    for thr in INFO_THRESHOLDS:  # jen informace
        rows, cv = simulate(market, s, e, 1, thr)
        m = metrics(cv, episodes(rows), START_EQUITY)
        m["ledger_sum_net_pnl"] = sum(r["net_pnl"] for r in rows)
        res["info_validation_x1"][f"z{thr}"] = m
        ledger += [{"variant": f"z{thr}", "period": "validation", "cost_multiplier": 1, **r} for r in rows]
    res["verdict"] = verdict(res)
    return res, ledger


def verdict(res):
    g = lambda p, m: res["strategy"][f"{p}/x{m}"]
    bh = lambda p, m: res["buy_hold"][f"{p}/x{m}"]["basket_50_50"]
    v1, v2, f2 = g("validation", 1), g("validation", 2), g("final_test", 2)
    checks = {
        "1_validation_sharpe_and_dd_beat_bh_x1": v1["sharpe"] > bh("validation", 1)["sharpe"]
        and v1["max_drawdown_pct"] < bh("validation", 1)["max_drawdown_pct"],
        "2_validation_episodes_ge_30": v1["trades"] >= 30,
        "3_validation_x2_pf_gt_1_2_and_net_gt_0": v2["profit_factor"] > 1.2 and v2["net_pnl"] > 0,
        "4_validation_x1_net_without_top3_gt_0": v1["net_without_top3"] > 0,
        "5_final_x2_net_gt_0_sharpe_and_dd_beat_bh": f2["net_pnl"] > 0
        and f2["sharpe"] > bh("final_test", 2)["sharpe"]
        and f2["max_drawdown_pct"] < bh("final_test", 2)["max_drawdown_pct"],
    }
    return {"checks": checks, "status": "KANDIDÁT NA FORWARD PAPER" if all(checks.values()) else "ZAMÍTNUTO"}


FIELDS = ["variant", "period", "cost_multiplier", "segment", "entry_day", "exit_day", "entry_reason", "exit_reason",
          "z_entry", "start_value", "end_value", "gross_pnl", "fees", "net_pnl"]


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
    lines = ["# Mean-reversion ETHBTC z20 ±2 (koš BTC/ETH) — výsledky (protokol `PROTOCOL.md`)", "",
             f"**Verdikt: {v['status']}** — jediná předem daná varianta (z20, práh ±2, výstup při z přes 0).", "",
             "| kritérium | splněno |", "|---|---|"]
    lines += [f"| {k} | {'ano' if ok else 'NE'} |" for k, ok in v["checks"].items()]
    lines += ["", "## Strategie vs. buy & hold koše BTC/ETH 50/50 (bez rebalance)", "",
              "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | epizody E/B | P/L epizod | PF epizod | bez top 3 | rozdíl vs B&H | B&H výnos % | B&H Sharpe | B&H max DD % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]["basket_50_50"]
            lines.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | "
                         f"{g['max_drawdown_pct']:.1f} | {g['trades']} | {g['episodes_net_pnl']:.2f} | {g['profit_factor']:.2f} | "
                         f"{g['net_without_top3']:.2f} | {g['excess_vs_bh_pnl']:.2f} | {b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    lines += ["", "## Informačně: B&H jednotlivých aktiv (×1)", "", "| období | BTC výnos % | BTC Sharpe | BTC DD % | ETH výnos % | ETH Sharpe | ETH DD % |",
              "|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        b = res["buy_hold"][f"{p}/x1"]
        lines.append(f"| {p} | {b['BTC_only']['return_pct']:.1f} | {b['BTC_only']['sharpe']:.2f} | {b['BTC_only']['max_drawdown_pct']:.1f} | "
                     f"{b['ETH_only']['return_pct']:.1f} | {b['ETH_only']['sharpe']:.2f} | {b['ETH_only']['max_drawdown_pct']:.1f} |")
    lines += ["", "## Informační prahy (validace ×1, NEJSOU kritériem, nic se nevybírá)", "",
              "| práh | čistý P/L | Sharpe | max DD % | epizody | P/L epizod | PF |", "|---|---|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
        lines.append(f"| {k} | {g['net_pnl']:.2f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} | {g['episodes_net_pnl']:.2f} | {g['profit_factor']:.2f} |")
    lines += ["", "Pozn.: `trades.csv` obsahuje i úseky N (koš 50/50); součet net_pnl všech řádků bloku = čistý P/L bloku.",
              "Obchody/PF/bez top 3 se počítají jen z epizod E/B; epizoda nese náklady obou svých přechodů.", "",
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
