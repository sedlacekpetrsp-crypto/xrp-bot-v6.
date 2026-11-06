"""RSI(2) pullback — křížový test na 8 dalších aktivech podle PROTOCOL.md (PAPER výzkum, veřejná data).

Pravidla se NEkopírují: používá se přímo research.rsi2_pullback.run (simulate, buy_hold, metrics).

    python -m research.rsi2_cross_asset.run --cache /tmp/vision-1d --outdir research/rsi2_cross_asset
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import urllib.error
from datetime import date
from pathlib import Path

from research.rsi2_pullback import run as base

SYMBOLS = ("SOLUSDT", "XRPUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT", "LTCUSDT", "AVAXUSDT")
FIRST_MONTH, LAST_MONTH = (2020, 1), (2026, 10)
SLEEVE_EQUITY = 10_000.0
N_TRIALS = 13


def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def load(cache, fetcher=base.fetch):
    market, manifest, missing = {}, [], []
    for s in SYMBOLS:
        bars = []
        for y, m in months():
            name = f"{s}-1d-{y}-{m:02d}.zip"
            url = f"https://data.binance.vision/data/spot/monthly/klines/{s}/1d/{name}"
            p = Path(cache) / name
            if not p.exists():
                try:
                    payload = fetcher(url)
                except urllib.error.HTTPError as e:
                    if e.code == 404:  # aktivum ještě nebylo listováno / archiv chybí
                        missing.append(name)
                        continue
                    raise
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(payload)
            payload = p.read_bytes()
            b = base.parse(payload)
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "bars": len(b)})
            bars.extend(b)
        dedup = {b["ts"]: b for b in bars}
        market[s] = [dedup[t] for t in sorted(dedup)]
    return market, manifest, missing


def period_dates(period):
    return tuple(date.fromisoformat(x) for x in base.PERIODS[period])


def combine(curves, start_each):
    days = sorted(set().union(*[c.keys() for c in curves]))
    out, last = {}, [None] * len(curves)
    for d in days:
        for j, c in enumerate(curves):
            if d in c:
                last[j] = c[d]
        out[d] = sum(v if v is not None else start_each for v in last)
    return out


def evaluate(market):
    res = {"per_asset": {}, "per_asset_bh": {}, "basket": {}, "basket_bh": {}, "daily_returns_validation_x1": None}
    ledger = []
    basket_sleeve = SLEEVE_EQUITY / len(SYMBOLS)
    for period in base.PERIODS:
        s, e = period_dates(period)
        for mult in base.COST_MULTIPLIERS:
            key = f"{period}/x{mult}"
            curves, bh_curves, all_tr = [], [], []
            for sym in SYMBOLS:
                bars = market[sym]
                if not [b for b in bars if s <= base.day(b["ts"]) <= e]:
                    continue
                tr, cv = base.simulate(bars, s, e, mult, sym, equity=SLEEVE_EQUITY)
                bh = base.buy_hold(bars, s, e, mult, equity=SLEEVE_EQUITY)
                res["per_asset"].setdefault(sym, {})[key] = base.metrics(cv, tr, SLEEVE_EQUITY)
                res["per_asset_bh"].setdefault(sym, {})[key] = base.metrics(bh, [], SLEEVE_EQUITY)
                ledger += [{"period": period, "cost_multiplier": mult, **t} for t in tr]
                # koš: stejné obchody, škálované na 12,5 % (simulace je lineární v kapitálu)
                f = basket_sleeve / SLEEVE_EQUITY
                curves.append({d: v * f for d, v in cv.items()})
                bh_curves.append({d: v * f for d, v in bh.items()})
                all_tr += [{**t, "net_pnl": t["net_pnl"] * f, "fees": t["fees"] * f} for t in tr]
            # chybějící aktivum (ještě nelistované) drží hotovost
            n_missing = len(SYMBOLS) - len(curves)
            basket = combine(curves, basket_sleeve)
            basket_bh = combine(bh_curves, basket_sleeve)
            if n_missing:
                basket = {d: v + n_missing * basket_sleeve for d, v in basket.items()}
                basket_bh = {d: v + n_missing * basket_sleeve for d, v in basket_bh.items()}
            res["basket"][key] = base.metrics(basket, all_tr, SLEEVE_EQUITY)
            res["basket"][key]["assets_in_period"] = len(curves)
            res["basket_bh"][key] = base.metrics(basket_bh, [], SLEEVE_EQUITY)
            if key == "validation/x1":
                vals = [basket[d] for d in sorted(basket)]
                res["daily_returns_validation_x1"] = [vals[0] / SLEEVE_EQUITY - 1] + \
                    [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    res["verdict"] = verdict(res)
    res["deflated_sharpe"] = dsr(res.pop("daily_returns_validation_x1"))
    return res, ledger


def asset_ok(res, sym):
    g, b = res["per_asset"][sym], res["per_asset_bh"][sym]
    try:
        return (g["validation/x2"]["net_pnl"] > 0 and g["final_test/x2"]["net_pnl"] > 0
                and g["validation/x2"]["max_drawdown_pct"] <= 0.6 * b["validation/x2"]["max_drawdown_pct"]
                and g["final_test/x2"]["max_drawdown_pct"] <= 0.6 * b["final_test/x2"]["max_drawdown_pct"])
    except KeyError:
        return False


def verdict(res):
    g, b = res["basket"], res["basket_bh"]
    checks = {
        "B1_validation_x2_net_gt_0_and_pf_gt_1_2": g["validation/x2"]["net_pnl"] > 0 and g["validation/x2"]["profit_factor"] > 1.2,
        "B2_dd_le_0_6_bh_validation_and_final": g["validation/x2"]["max_drawdown_pct"] <= 0.6 * b["validation/x2"]["max_drawdown_pct"]
        and g["final_test/x2"]["max_drawdown_pct"] <= 0.6 * b["final_test/x2"]["max_drawdown_pct"],
        "B3_final_x2_net_gt_0": g["final_test/x2"]["net_pnl"] > 0,
        "B4_validation_x1_without_top3_gt_0": g["validation/x1"]["net_without_top3"] > 0,
        "B5_trades_validation_plus_final_ge_20": g["validation/x1"]["trades"] + g["final_test/x1"]["trades"] >= 20,
        "B6_tuning_x1_net_gt_0": g["tuning/x1"]["net_pnl"] > 0,
    }
    positive_both = [s for s in res["per_asset"]
                     if res["per_asset"][s].get("validation/x2", {}).get("net_pnl", -1) > 0
                     and res["per_asset"][s].get("final_test/x2", {}).get("net_pnl", -1) > 0]
    return {"basket_track_b": checks,
            "basket_status": "PROŠLO (stopa B, post-hoc) ⇒ forward PAPER" if all(checks.values()) else "ZAMÍTNUTO",
            "assets_added_to_forward": [s for s in SYMBOLS if s in res["per_asset"] and asset_ok(res, s)],
            "assets_positive_validation_and_final_x2": positive_both}


def dsr(returns):
    p = Path(__file__).resolve().parents[2] / "tools" / "research" / "deflated_sharpe.py"
    if not p.exists() or not returns:
        return {"available": False}
    spec = importlib.util.spec_from_file_location("deflated_sharpe", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # rozptyl SR přes pokusy neznáme přesně ⇒ konzervativně: rozptyl odhadnutý z denních SR = 1/T
    t = len(returns)
    out = m.dsr_from_returns(returns, N_TRIALS, 1.0 / t)
    return {"available": True, "n_trials": N_TRIALS, "var_trials": 1.0 / t, "result": out}


def write(outdir, res, ledger, manifest, missing):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    fields = ["period", "cost_multiplier", "symbol", "entry_day", "exit_day", "exit_reason", "entry_px",
              "exit_px", "qty", "gross_pnl", "fees", "net_pnl"]
    with (out / "trades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(ledger)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (out / "data_source.json").write_text(json.dumps(
        {"source": "https://data.binance.vision spot monthly 1d klines (public, no keys)",
         "archives": manifest, "missing_archives_404": missing}, indent=0) + "\n")
    (out / "RESULTS.md").write_text(report(res))


def fmt(x):
    return f"{x:.1f}"


def report(res):
    v = res["verdict"]
    L = ["# RSI(2) pullback — křížový test na 8 aktivech (protokol `PROTOCOL.md`)", "",
         f"**Koš, stopa B: {v['basket_status']}**", "",
         "| kritérium (koš) | splněno |", "|---|---|"]
    L += [f"| {k} | {'ano' if ok else 'NE'} |" for k, ok in v["basket_track_b"].items()]
    L += ["", f"Aktiva přidaná do forward PAPER (pravidlo protokolu): **{', '.join(v['assets_added_to_forward']) or 'žádné'}**",
          f"Aktiva se ziskem ve validaci ×2 i závěrečném ×2: {', '.join(v['assets_positive_validation_and_final_x2']) or 'žádné'}", "",
          "## Koš 8 × 12,5 % vs buy & hold", "",
          "| období | náklady | výnos % | Sharpe | max DD % | obchody | PF | B&H výnos % | B&H DD % |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in base.PERIODS:
        for m in base.COST_MULTIPLIERS:
            g, b = res["basket"][f"{p}/x{m}"], res["basket_bh"][f"{p}/x{m}"]
            L.append(f"| {p} | ×{m} | {fmt(g['return_pct'])} | {g['sharpe']:.2f} | {fmt(g['max_drawdown_pct'])} | "
                     f"{g['trades']} | {g['profit_factor']:.2f} | {fmt(b['return_pct'])} | {fmt(b['max_drawdown_pct'])} |")
    L += ["", "## Jednotlivá aktiva (náklady ×2)", "",
          "| aktivum | validace % | DD % | B&H % | B&H DD % | závěr. % | DD % | B&H % | B&H DD % | obchody V+Z | do forwardu |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in SYMBOLS:
        g, b = res["per_asset"].get(s, {}), res["per_asset_bh"].get(s, {})
        if "validation/x2" not in g or "final_test/x2" not in g:
            L.append(f"| {s} | – | – | – | – | – | – | – | – | – | NE (chybí data) |")
            continue
        gv, gf, bv, bf = g["validation/x2"], g["final_test/x2"], b["validation/x2"], b["final_test/x2"]
        L.append(f"| {s} | {fmt(gv['return_pct'])} | {fmt(gv['max_drawdown_pct'])} | {fmt(bv['return_pct'])} | "
                 f"{fmt(bv['max_drawdown_pct'])} | {fmt(gf['return_pct'])} | {fmt(gf['max_drawdown_pct'])} | "
                 f"{fmt(bf['return_pct'])} | {fmt(bf['max_drawdown_pct'])} | {gv['trades'] + gf['trades']} | "
                 f"{'ano' if s in v['assets_added_to_forward'] else 'NE'} |")
    d = res.get("deflated_sharpe", {})
    L += ["", f"Deflated Sharpe (koš, validace ×1, N = {N_TRIALS}): `{json.dumps(d.get('result'), default=str)}`" if d.get("available")
          else "Deflated Sharpe: nástroj nedostupný.", "",
          "Výsledek je post-hoc vůči RSI(2) na BTC/ETH (PR #13). Výhradně PAPER výzkum — ani „prošlo“ neznamená ziskovou strategii.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    market, manifest, missing = load(a.cache)
    res, ledger = evaluate(market)
    write(a.outdir, res, ledger, manifest, missing)
    print(json.dumps({"verdict": res["verdict"], "trades": len(ledger), "missing": len(missing)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
