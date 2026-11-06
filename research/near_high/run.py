"""Blízkost 52týdennímu maximu průřezově, 8 aktiv — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.near_high.run --cache /tmp/vision-1d --outdir research/near_high

Loader a metriky převzaty z research/vol_target/run.py (PR #27). Simulace nová: měsíční výběr K aktiv
s nejvyšším close/max365(close), stejné váhy, plné přerozdělení za open prvního dne měsíce.
„Obchod“ = slot aktiva v měsíci (souvislý ledger, součet net_pnl = P/L bloku).
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
K = 3
NEIGHBORS = (2, 4)
LOOKBACK = 365
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
DSR_N, DSR_VAR_ANNUAL = 151, 0.5


# ------------------------------------------------------------------ data (jako PR #27)
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
def score_series(bars, lookback=LOOKBACK):
    """Skóre(t) = close(t) / max(close(t−lookback+1 … t)); jen dny s plným oknem a bez mezer."""
    closes = [(day(b["ts"]), b["close"]) for b in bars]
    out = {}
    for i in range(lookback - 1, len(closes)):
        if (closes[i][0] - closes[i - lookback + 1][0]).days != lookback - 1:
            continue
        mx = max(c for _, c in closes[i - lookback + 1:i + 1])
        out[closes[i][0]] = closes[i][1] / mx
    return out


def select(scores, d, k, bottom=False):
    """Top-k (nebo bottom-k) podle skóre k close dne d; shoda ⇒ pořadí v SYMBOLS."""
    for s in SYMBOLS:
        if d not in scores[s]:
            raise ValueError(f"chybí skóre {s} {d}")
    order = sorted(range(len(SYMBOLS)),
                   key=lambda i: ((scores[SYMBOLS[i]][d] if bottom else -scores[SYMBOLS[i]][d]), i))
    return [SYMBOLS[i] for i in order[:k]]


def rebalance_days(start, end):
    """Den startu + první den každého dalšího měsíce v období."""
    out, d = [start], date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    while d <= end:
        out.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


# ------------------------------------------------------------------ simulace
def simulate(market, scores, start, end, mult, k=K, bottom=False, chooser=None, equity=START_EQUITY):
    """Vrací (rows, curve). chooser(d_signal) → seznam aktiv (pro rovnovážný koš); jinak top/bottom-k."""
    fee, slip = FEE * mult, SLIP * mult
    k_buy = 1 / ((1 + slip) * (1 + fee))
    k_sell = (1 - slip) * (1 - fee)
    px = {s: by_day(market[s]) for s in SYMBOLS}
    days, d = [], start
    while d <= end:
        for s in SYMBOLS:
            if d not in px[s]:
                raise ValueError(f"chybí svíčka {s} {d}")
        days.append(d)
        d += timedelta(days=1)
    rset = set(rebalance_days(start, end))

    qty = {s: 0.0 for s in SYMBOLS}
    cash = equity
    rows, curve, open_legs = [], {}, {}
    for j, d in enumerate(days):
        if d in rset:
            sig_day = d - timedelta(days=1)
            names = chooser(sig_day) if chooser else select(scores, sig_day, k, bottom)
            o = {s: px[s][d]["open"] for s in SYMBOLS}
            before = cash + sum(qty[s] * o[s] for s in SYMBOLS)
            # uzavřít sloty minulého měsíce (end_value = hodnota za open před rebalance)
            for s, leg in open_legs.items():
                ev = qty[s] * o[s] + leg.get("cash_carried", 0.0)
                rows.append({**leg, "exit_day": d.isoformat(), "end_value": ev,
                             "net_pnl": ev - leg["start_value"], "gross_pnl": ev - leg["start_value"] + leg["fees"]})
            open_legs = {}
            tgt = before / len(names)
            # nejdřív prodeje (hotovost), pak nákupy; cílová hodnota před náklady = before/len(names)
            for s in SYMBOLS:
                cur = qty[s] * o[s]
                want = tgt if s in names else 0.0
                if cur > want:
                    x = cur - want
                    qty[s] -= x / o[s]
                    cash += x * k_sell
            for s in names:
                cur = qty[s] * o[s]
                if tgt > cur:
                    x = min(tgt - cur, cash)
                    cash -= x
                    qty[s] += x * k_buy / o[s]
            after = cash + sum(qty[s] * o[s] for s in SYMBOLS)
            cost = before - after
            # zbytková hotovost (z nákladů) zůstane; přičte se k prvnímu slotu, aby ledger seděl
            for i, s in enumerate(names):
                sv = qty[s] * o[s] + cost / len(names) + (cash if i == 0 else 0.0)
                sc = scores.get(s, {}).get(sig_day)
                open_legs[s] = {"asset": s, "entry_day": d.isoformat(),
                                "score_entry": round(sc, 4) if sc is not None else None,
                                "start_value": sv, "fees": cost / len(names)}
            if cash:
                q0 = names[0]
                open_legs[q0]["cash_carried"] = cash
        c = {s: px[s][d]["close"] for s in SYMBOLS}
        v = cash + sum(qty[s] * c[s] for s in SYMBOLS)
        if j == len(days) - 1:
            total = cash
            for s, leg in open_legs.items():
                ev = qty[s] * c[s] * k_sell + leg.get("cash_carried", 0.0)
                liq = qty[s] * c[s] * (1 - k_sell)
                total += qty[s] * c[s] * k_sell
                leg["fees"] += liq
                rows.append({**leg, "exit_day": d.isoformat(), "end_value": ev,
                             "net_pnl": ev - leg["start_value"], "gross_pnl": ev - leg["start_value"] + leg["fees"]})
            curve[d] = total
        else:
            curve[d] = v
    # hotovost přenášená v slotu: start_value i end_value ji obsahují (neutrální pro P/L slotu kromě posledního)
    for r in rows:
        r.pop("cash_carried", None)
    return rows, curve


def buy_hold_basket(market, start, end, mult, equity=START_EQUITY):
    fee, slip = FEE * mult, SLIP * mult
    px = {s: by_day(market[s]) for s in SYMBOLS}
    q = {s: (equity / len(SYMBOLS)) / (px[s][start]["open"] * (1 + slip) * (1 + fee)) for s in SYMBOLS}
    curve, d = {}, start
    while d <= end:
        v = sum(q[s] * px[s][d]["close"] for s in SYMBOLS)
        if d == end:
            v *= (1 - slip) * (1 - fee)
        curve[d] = v
        d += timedelta(days=1)
    return curve


def buy_hold_single(bars, start, end, mult, equity=START_EQUITY):
    fee, slip = FEE * mult, SLIP * mult
    sel = [b for b in bars if start <= day(b["ts"]) <= end]
    q = equity / (sel[0]["open"] * (1 + slip) * (1 + fee))
    curve = {}
    for j, b in enumerate(sel):
        v = q * b["close"]
        if j == len(sel) - 1:
            v *= (1 - slip) * (1 - fee)
        curve[day(b["ts"])] = v
    return curve


# ------------------------------------------------------------------ metriky (jako PR #27)
def daily_returns(curve, start_equity):
    vals = [curve[d] for d in sorted(curve)]
    return [vals[0] / start_equity - 1] + [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]


def metrics(curve, trades, start_equity=START_EQUITY):
    vals = [curve[d] for d in sorted(curve)]
    rets = daily_returns(curve, start_equity)
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
            "ledger_sum_net_pnl": sum(nets),
            "profit_factor": (gw / gl) if gl > 0 else (math.inf if gw > 0 else 0.0),
            "win_rate_pct": 100 * sum(1 for x in nets if x > 0) / len(nets) if nets else 0.0,
            "net_without_top3": sum(nets[3:]) if len(nets) > 3 else 0.0,
            "fees": sum(t["fees"] for t in trades)}


def span(period):
    return tuple(date.fromisoformat(x) for x in PERIODS[period])


def evaluate(market):
    scores = {s: score_series(market[s]) for s in SYMBOLS}
    res = {"strategy": {}, "buy_hold": {}, "neighbors_validation_x2": {}, "walk_forward_x2": {}, "info_validation_x1": {}}
    ledger, val_curve = [], None

    def run(s, e, mult, tag, **kw):
        rows, cv = simulate(market, scores, s, e, mult, **kw)
        ledger.extend({**tag, **r} for r in rows)
        return metrics(cv, rows), cv

    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            bh = metrics(buy_hold_basket(market, s, e, mult), [])
            res["buy_hold"][f"{period}/x{mult}"] = bh
            m, cv = run(s, e, mult, {"variant": f"TOP{K}", "period": period, "cost_multiplier": mult})
            m["excess_vs_bh_pnl"] = m["net_pnl"] - bh["net_pnl"]
            res["strategy"][f"{period}/x{mult}"] = m
            if period == "validation" and mult == 1:
                val_curve = cv
    s, e = span("validation")
    for k in NEIGHBORS:
        m, _ = run(s, e, 2, {"variant": f"TOP{k}", "period": "validation", "cost_multiplier": 2}, k=k)
        res["neighbors_validation_x2"][f"TOP{k}"] = m
    for y in WF_YEARS:
        ys, ye = date(y, 1, 1), date(y, 12, 31)
        m, _ = run(ys, ye, 2, {"variant": f"TOP{K}", "period": f"wf_{y}", "cost_multiplier": 2})
        m["bh"] = metrics(buy_hold_basket(market, ys, ye, 2), [])
        res["walk_forward_x2"][str(y)] = m
    m, _ = run(s, e, 1, {"variant": f"BOTTOM{K}", "period": "validation", "cost_multiplier": 1}, bottom=True)
    res["info_validation_x1"][f"placebo_BOTTOM{K}"] = m
    m, _ = run(s, e, 1, {"variant": "EQW8_MONTHLY", "period": "validation", "cost_multiplier": 1},
               chooser=lambda _d: list(SYMBOLS))
    res["info_validation_x1"]["EQW8_monthly_rebalance"] = m
    res["info_validation_x1"]["BH_BTC"] = metrics(buy_hold_single(market["BTCUSDT"], s, e, 1), [])

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


FIELDS = ["variant", "period", "cost_multiplier", "asset", "entry_day", "exit_day", "score_entry",
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
    L = ["# Blízkost 52týdennímu maximu, 8 aktiv — výsledky (protokol `PROTOCOL.md`)", "",
         f"**Verdikt: {v['status']}** — jediná varianta top {K}, měsíčně, stejné váhy, 100 % investováno.", "",
         "| kritérium | splněno |", "|---|---|"]
    L += [f"| {k} | {yn(ok)} |" for k, ok in {**v["track_a"], **v["track_b"], **v["robustness"]}.items()]
    L += ["", f"DSR validace ×1 (N = {DSR_N}): {res['dsr_validation_x1']['dsr']:.3f}; walk-forward kladných let: "
          f"{v['walk_forward_positive_years']}/4.", "",
          "## Strategie vs. buy & hold rovnovážného koše 8 aktiv", "",
          "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | bez top 3 | poplatky | B&H výnos % | B&H Sharpe | B&H DD % |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]
            L.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | "
                     f"{g['trades']} | {g['profit_factor']:.2f} | {g['net_without_top3']:.2f} | {g['fees']:.2f} | "
                     f"{b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    L += ["", "## Robustnost", "", "| test | čistý P/L | výnos % | Sharpe | DD % | obchody |", "|---|---|---|---|---|---|"]
    for k, g in res["neighbors_validation_x2"].items():
        L.append(f"| soused {k}, validace ×2 | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    for y, g in res["walk_forward_x2"].items():
        L.append(f"| WF {y} ×2 (B&H {g['bh']['return_pct']:.1f} %) | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "## Informačně (validace ×1, NEJSOU kritériem)", "",
          "| varianta | výnos % | Sharpe | DD % | obchody |", "|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
        L.append(f"| {k} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "Pozn.: `trades.csv` = slot aktiva v měsíci; součet net_pnl bloku (variant, period, cost_multiplier) = čistý P/L bloku.",
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
