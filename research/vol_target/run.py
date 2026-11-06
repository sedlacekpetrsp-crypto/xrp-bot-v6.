"""Volatilitní cílení BTC 40 % (long-only, bez páky) — backtest podle PROTOCOL.md (+ dodatek 1).
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.vol_target.run --cache /tmp/vision-1d --outdir research/vol_target

Loader převzat z research/ethbtc_meanrev/run.py (PR #20). Simulace nová: w*(t) = min(1, cíl/σ30(t)),
úprava za open(t+1) jen při |w* − w| > 0,10. „Obchod“ = úsek mezi úpravami (souvislý ledger).
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

SYMBOLS = ("BTCUSDT", "ETHUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
TARGET = 0.40
NEIGHBORS = (0.30, 0.50)
INFO_TARGETS = (0.30, 0.60)
BAND = 0.10
VOL_WINDOW = 30
PERIODS = {"tuning": ("2020-09-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
DSR_N, DSR_VAR_ANNUAL = 148, 0.5


# ------------------------------------------------------------------ data (beze změny z PR #20)
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
def sigma_series(bars, window=VOL_WINDOW):
    """σ(t) = výběrová sd (ddof=1) `window` denních log-výnosů close, okno končí close t, × √365."""
    closes = [(day(b["ts"]), b["close"]) for b in bars]
    out = {}
    for i in range(window, len(closes)):
        r = [math.log(closes[j][1] / closes[j - 1][1]) for j in range(i - window + 1, i + 1)]
        mu = sum(r) / window
        out[closes[i][0]] = math.sqrt(sum((x - mu) ** 2 for x in r) / (window - 1)) * math.sqrt(365)
    return out


def target_weight(sigma, target):
    return min(1.0, target / sigma) if sigma > 0 else 1.0


# ------------------------------------------------------------------ simulace
def simulate(bars, start, end, mult, target=TARGET, equity=START_EQUITY):
    """Vrací (rows, curve). rows = úseky mezi úpravami; start_value úseku = hodnota portfolia PŘED úpravou, která
    předchozí úsek ukončila … přesněji: úsek končí hodnotou PO úpravě (náklady úpravy nese končící úsek),
    další úsek začíná touto hodnotou ⇒ součet net_pnl = konečná hodnota − počáteční kapitál."""
    fee, slip = FEE * mult, SLIP * mult
    k_buy = 1 / ((1 + slip) * (1 + fee))
    k_sell = (1 - slip) * (1 - fee)
    px = by_day(bars)
    sig = sigma_series(bars)
    days, d = [], start
    while d <= end:
        if d not in px:
            raise ValueError(f"chybí svíčka {d}")
        days.append(d)
        d += timedelta(days=1)
    prev = start - timedelta(days=1)
    if prev not in sig:
        raise ValueError(f"chybí σ pro {prev}")

    rows, curve = [], {}
    qty, cash = 0.0, equity
    seg = None
    pending = target_weight(sig[prev], target)  # počáteční nákup za open prvního dne

    def trade_to(w_new, o):
        nonlocal qty, cash
        before = qty * o + cash
        cur = qty * o
        tgt = w_new * before
        if tgt > cur:
            x = tgt - cur
            cash -= x
            qty += x * k_buy / o
        elif tgt < cur:
            x = cur - tgt
            qty -= x / o
            cash += x * k_sell
        return before, qty * o + cash

    for j, d in enumerate(days):
        b = px[d]
        o, c = b["open"], b["close"]
        if pending is not None:
            w_old = (qty * o) / (qty * o + cash) if (qty * o + cash) > 0 else 0.0
            before, after = trade_to(pending, o)
            cost = before - after
            if seg is None:
                seg = {"entry_day": d.isoformat(), "entry_reason": "period_start", "start_value": equity,
                       "w_from": 0.0, "w_to": round(pending, 4), "sigma_entry": round(sig[prev], 4), "fees": cost}
            else:
                seg["fees"] += cost
                net = after - seg["start_value"]
                rows.append({**seg, "exit_day": d.isoformat(), "exit_reason": f"rebalance {w_old:.3f}->{pending:.3f}",
                             "end_value": after, "gross_pnl": net + seg["fees"], "net_pnl": net})
                seg = {"entry_day": d.isoformat(), "entry_reason": f"rebalance {w_old:.3f}->{pending:.3f}",
                       "start_value": after, "w_from": round(w_old, 4), "w_to": round(pending, 4),
                       "sigma_entry": round(sig[days[j - 1]], 4), "fees": 0.0}
            pending = None
        v = qty * c + cash
        if j == len(days) - 1:
            total = qty * c * k_sell + cash
            seg["fees"] += v - total
            net = total - seg["start_value"]
            rows.append({**seg, "exit_day": d.isoformat(), "exit_reason": "period_end", "end_value": total,
                         "gross_pnl": net + seg["fees"], "net_pnl": net})
            curve[d] = total
        else:
            curve[d] = v
            if d not in sig:
                raise ValueError(f"chybí σ pro {d}")
            w_star = target_weight(sig[d], target)
            w_now = (qty * c) / v if v > 0 else 0.0
            if abs(w_star - w_now) > BAND:
                pending = w_star
    return rows, curve


def buy_hold(bars, start, end, mult, equity=START_EQUITY):
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


# ------------------------------------------------------------------ metriky (jako PR #20)
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
            "fees": sum(t["fees"] for t in trades),
            "avg_weight_in": None}


def span(period):
    return tuple(date.fromisoformat(x) for x in PERIODS[period])


def run(bars, s, e, mult, target, ledger, tag):
    rows, cv = simulate(bars, s, e, mult, target)
    m = metrics(cv, rows)
    # průměrná expozice (časově vážená podle úseků)
    tot = sum((date.fromisoformat(r["exit_day"]) - date.fromisoformat(r["entry_day"])).days or 1 for r in rows)
    m["avg_weight_in"] = sum(r["w_to"] * ((date.fromisoformat(r["exit_day"]) - date.fromisoformat(r["entry_day"])).days or 1)
                             for r in rows) / tot
    ledger += [{**tag, **r} for r in rows]
    return m, cv


def evaluate(market):
    btc, eth = market["BTCUSDT"], market["ETHUSDT"]
    tg = f"T{int(TARGET * 100)}"
    res = {"strategy": {}, "buy_hold": {}, "neighbors_validation_x2": {}, "walk_forward_x2": {},
           "info_validation_x1": {}}
    ledger, val_curve = [], None
    for period in PERIODS:
        s, e = span(period)
        for mult in COST_MULTIPLIERS:
            bh = metrics(buy_hold(btc, s, e, mult), [])
            res["buy_hold"][f"{period}/x{mult}"] = bh
            m, cv = run(btc, s, e, mult, TARGET, ledger,
                        {"variant": f"BTC_{tg}", "period": period, "cost_multiplier": mult})
            m["excess_vs_bh_pnl"] = m["net_pnl"] - bh["net_pnl"]
            res["strategy"][f"{period}/x{mult}"] = m
            if period == "validation" and mult == 1:
                val_curve = cv
    s, e = span("validation")
    for t in NEIGHBORS:
        m, _ = run(btc, s, e, 2, t, ledger, {"variant": f"BTC_T{int(t * 100)}", "period": "validation", "cost_multiplier": 2})
        res["neighbors_validation_x2"][f"T{int(t * 100)}"] = m
    for y in WF_YEARS:
        m, _ = run(btc, date(y, 1, 1), date(y, 12, 31), 2, TARGET, ledger,
                   {"variant": f"BTC_{tg}", "period": f"wf_{y}", "cost_multiplier": 2})
        m["bh"] = metrics(buy_hold(btc, date(y, 1, 1), date(y, 12, 31), 2), [])
        res["walk_forward_x2"][str(y)] = m
    for t in INFO_TARGETS:
        m, _ = run(btc, s, e, 1, t, ledger, {"variant": f"BTC_T{int(t * 100)}", "period": "validation", "cost_multiplier": 1})
        res["info_validation_x1"][f"BTC_T{int(t * 100)}"] = m
    m, _ = run(eth, s, e, 1, TARGET, ledger, {"variant": f"ETH_{tg}", "period": "validation", "cost_multiplier": 1})
    m["bh"] = metrics(buy_hold(eth, s, e, 1), [])
    res["info_validation_x1"][f"ETH_{tg}"] = m

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


FIELDS = ["variant", "period", "cost_multiplier", "entry_day", "exit_day", "entry_reason", "exit_reason",
          "w_from", "w_to", "sigma_entry", "start_value", "end_value", "gross_pnl", "fees", "net_pnl"]


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
    yn = lambda ok: "ano" if ok else "NE"
    L = ["# Volatilitní cílení BTC 40 % — výsledky (protokol `PROTOCOL.md` + dodatek 1)", "",
         f"**Verdikt: {v['status']}** — jediná varianta cíl 40 %, pásmo ±10 p. b., σ30, long-only bez páky.", "",
         "| kritérium | splněno |", "|---|---|"]
    L += [f"| {k} | {yn(ok)} |" for k, ok in {**v["track_a"], **v["track_b"], **v["robustness"]}.items()]
    L += ["", f"DSR validace ×1 (N = {DSR_N}): {res['dsr_validation_x1']['dsr']:.3f}; walk-forward kladných let: "
          f"{v['walk_forward_positive_years']}/4.", "",
          "## Strategie vs. buy & hold BTC", "",
          "| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | úseky | PF | bez top 3 | poplatky | prům. váha | B&H výnos % | B&H Sharpe | B&H DD % |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in PERIODS:
        for m in COST_MULTIPLIERS:
            g, b = res["strategy"][f"{p}/x{m}"], res["buy_hold"][f"{p}/x{m}"]
            L.append(f"| {p} | ×{m} | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | "
                     f"{g['trades']} | {g['profit_factor']:.2f} | {g['net_without_top3']:.2f} | {g['fees']:.2f} | {g['avg_weight_in']:.2f} | "
                     f"{b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    L += ["", "## Robustnost", "", "| test | čistý P/L | výnos % | Sharpe | DD % | úseky |", "|---|---|---|---|---|---|"]
    for k, g in res["neighbors_validation_x2"].items():
        L.append(f"| soused {k}, validace ×2 | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    for y, g in res["walk_forward_x2"].items():
        L.append(f"| WF {y} ×2 (B&H {g['bh']['return_pct']:.1f} %) | {g['net_pnl']:.2f} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} |")
    L += ["", "## Informačně (validace ×1, NEJSOU kritériem, nic se nevybírá)", "",
          "| varianta | výnos % | Sharpe | DD % | úseky | B&H výnos % | B&H Sharpe | B&H DD % |", "|---|---|---|---|---|---|---|---|"]
    for k, g in res["info_validation_x1"].items():
        b = g.get("bh") or res["buy_hold"]["validation/x1"]
        L.append(f"| {k} | {g['return_pct']:.1f} | {g['sharpe']:.2f} | {g['max_drawdown_pct']:.1f} | {g['trades']} | "
                 f"{b['return_pct']:.1f} | {b['sharpe']:.2f} | {b['max_drawdown_pct']:.1f} |")
    L += ["", "Pozn.: `trades.csv` = úseky mezi úpravami; součet net_pnl bloku (variant, period, cost_multiplier) = čistý P/L bloku.",
          "Úsek nese náklady úpravy, která ho ukončuje (první i počáteční nákup, poslední i likvidaci).", "",
          "Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.", ""]
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
