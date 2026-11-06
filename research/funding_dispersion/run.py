"""Průřezová disperze fundingu, koš 8 USDT-M perpů (H-20261106-2) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.funding_dispersion.run --cache /tmp/vision-fd --outdir research/funding_dispersion
"""
import argparse
import bisect
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

ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT")
FIRST_MONTH = (2020, 8)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
GRID = [(w, h) for w in (7, 14) for h in (7, 14)]  # (W okno fundingu, H držení) ve dnech
PERIODS = {"tuning": ("2020-10-05", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
LEG_FRACTION = 0.10
N_SIDE = 2
MIN_ELIGIBLE = 6
FALLBACK_HOURS = 6
DSR_N, DSR_VAR_ANNUAL = 159, 0.5
HOUR_MS = 3_600_000
DAY_MS = 86_400_000


def vt(w, h):
    return f"W{w}_H{h}"


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


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


def parse_klines(payload):
    return [(_ms(int(r[0])), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in _csv_rows(payload)]


def normalize_funding_ts(ts):
    """Na celou hodinu jen při odchylce ≤ 1 s (konvence repozitáře), jinak chyba."""
    near = round(ts / HOUR_MS) * HOUR_MS
    if abs(ts - near) > 1000:
        raise ValueError(f"funding timestamp {ts} je {ts - near} ms od celé hodiny")
    return near


def parse_funding(payload):
    """Binance Vision fundingRate: calc_time, funding_interval_hours, last_funding_rate."""
    return [(normalize_funding_ts(_ms(int(r[0]))), float(r[2])) for r in _csv_rows(payload)]


def urls(asset):
    base = "https://data.binance.vision/data/futures/um/monthly"
    for y, m in months():
        tag = f"{y}-{m:02d}"
        yield "kl", (y, m), f"{base}/klines/{asset}/1h/{asset}-1h-{tag}.zip"
        yield "fr", (y, m), f"{base}/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"


def load(cache, fetcher=fetch):
    market, manifest, missing, fatal = {}, [], [], []
    for a in ASSETS:
        bars, fund, present = {}, {}, {"kl": [], "fr": []}
        miss = {"kl": [], "fr": []}
        for kind, ym, url in urls(a):
            p = Path(cache) / kind / url.rsplit("/", 1)[1]
            if not p.exists():
                try:
                    payload = fetcher(url)
                except urllib.error.HTTPError as e:
                    missing.append({"url": url, "http": e.code})
                    miss[kind].append(ym)
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(payload)
            payload = p.read_bytes()
            present[kind].append(ym)
            if kind == "kl":
                rows = parse_klines(payload)
                for r in rows:
                    bars[r[0]] = r[1:]
            else:
                rows = parse_funding(payload)
                for ts, rate in rows:
                    fund[ts] = rate
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
        for kind in ("kl", "fr"):
            # povolené jsou jen chybějící měsíce PŘED prvním existujícím (kontrakt ještě neobchodoval)
            if present[kind]:
                first = min(present[kind])
                fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
            else:
                fatal.append({"asset": a, "kind": kind, "month": "all"})
        market[a] = prepare(bars, fund)
    return market, manifest, missing, fatal


def prepare(bars, fund):
    """bars {ts: (o, h, l, c)}, fund {ts: rate} → struktura s indexy pro rychlé kauzální dotazy."""
    funding = dict(sorted(fund.items()))
    fts = list(funding)
    cum = [0.0]
    for ts in fts:
        cum.append(cum[-1] + funding[ts])
    return {"bars": bars, "funding": funding, "fts": fts, "fcum": cum,
            "first_bar": min(bars) if bars else None, "first_funding": fts[0] if fts else None}


# ------------------------------------------------------------------ simulace
def ms_of(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def date_of(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def first_monday_on_or_after(d):
    return d + timedelta(days=(7 - d.weekday()) % 7)


class Prices:
    def __init__(self, market):
        self.m = market
        self.fallbacks = 0

    def get(self, a, t, field):
        """field: 0 open, 1 high, 2 low, 3 close. Chybí-li svíčka v t: close nejbližší dřívější do 6 h (dodatek 0)."""
        b = self.m[a]["bars"].get(t)
        if b is not None:
            return b[field]
        for k in range(1, FALLBACK_HOURS + 1):
            b = self.m[a]["bars"].get(t - k * HOUR_MS)
            if b is not None:
                self.fallbacks += 1
                return b[3]
        raise KeyError(f"chybí cena {a} {datetime.fromtimestamp(t / 1000, tz=timezone.utc)}")


def funding_signal(m, D, W):
    """Součet sazeb vypořádaných v (D − W dní, D] — jen známé k D."""
    lo = D - W * DAY_MS
    i, j = bisect.bisect_right(m["fts"], lo), bisect.bisect_right(m["fts"], D)
    return m["fcum"][j] - m["fcum"][i]


def eligible(market, a, D, W, entry_ts):
    m = market[a]
    if m["first_funding"] is None or m["first_bar"] is None:
        return False
    lo = D - W * DAY_MS
    return m["first_funding"] <= lo and m["first_bar"] <= lo and entry_ts in m["bars"]


def select_legs(signals):
    order = sorted(signals.items(), key=lambda kv: (kv[1], kv[0]))
    longs = [a for a, _ in order[:N_SIDE]]
    shorts = [a for a, _ in order[-N_SIDE:]]
    return longs, shorts


def simulate(market, start, end, W, H, mult, variant="", prices=None):
    """Vrací (nohy, denní equity {date: value}, rozhodnutí)."""
    px = prices or Prices(market)
    c = (FEE + SLIP) * mult
    end_ms = ms_of(end) + DAY_MS
    D = ms_of(first_monday_on_or_after(start))
    first_decision = D
    cash = START_EQUITY
    legs, curve, decisions = [], {}, []
    while True:
        entry_ts, exit_ts = D + HOUR_MS, D + H * DAY_MS + HOUR_MS
        if exit_ts > end_ms - HOUR_MS:  # výstupní svíčka musí ležet v období
            break
        elig = [a for a in ASSETS if eligible(market, a, D, W, entry_ts)]
        if len(elig) < MIN_ELIGIBLE:
            decisions.append({"decision": date_of(D).isoformat(), "skipped": True, "eligible": len(elig)})
            for k in range(7):
                curve[date_of(D + k * DAY_MS)] = cash
            D += 7 * DAY_MS
            continue
        sig = {a: funding_signal(market[a], D, W) for a in elig}
        longs, shorts = select_legs(sig)
        decisions.append({"decision": date_of(D).isoformat(), "skipped": False, "eligible": len(elig),
                          "longs": longs, "shorts": shorts, "signal": sig})
        equity0 = cash
        open_legs = []
        for side, names in ((1, longs), (-1, shorts)):
            for a in names:
                e = px.get(a, entry_ts, 0)
                notional = LEG_FRACTION * equity0
                cost_in = notional * c
                cash -= cost_in
                open_legs.append({"period_variant": variant, "asset": a, "side": side, "entry_ts": entry_ts,
                                  "entry": e, "qty": notional / e, "notional": notional, "costs": cost_in,
                                  "funding": 0.0, "liquidated": 0, "alive": True, "signal": sig[a]})
        t = entry_ts
        while t < exit_ts:
            for lg in open_legs:
                if not lg["alive"]:
                    continue
                a = lg["asset"]
                if t > entry_ts and t in market[a]["funding"]:
                    amt = -lg["side"] * market[a]["funding"][t] * lg["qty"] * px.get(a, t, 0)
                    lg["funding"] += amt
                if lg["side"] == -1 and px.get(a, t, 1) >= 2 * lg["entry"]:
                    lg.update(alive=False, liquidated=1, exit_ts=t, exit=2 * lg["entry"],
                              gross=-lg["notional"])
                    cash += lg["gross"] + lg["funding"]
            if (t // HOUR_MS) % 24 == 23:  # close svíčky 23:00 = konec dne
                mtm = sum(lg["side"] * lg["qty"] * (px.get(lg["asset"], t, 3) - lg["entry"]) + lg["funding"]
                          for lg in open_legs if lg["alive"])
                curve[date_of(t)] = cash + mtm
            t += HOUR_MS
        for lg in open_legs:
            if lg["alive"]:
                x = px.get(lg["asset"], exit_ts, 0)
                cost_out = lg["qty"] * x * c
                lg.update(alive=False, exit_ts=exit_ts, exit=x, gross=lg["side"] * lg["qty"] * (x - lg["entry"]))
                lg["costs"] += cost_out
                cash += lg["gross"] + lg["funding"] - cost_out
            lg["net_pnl"] = lg["gross"] + lg["funding"] - lg["costs"]
            legs.append(lg)
        D += H * DAY_MS
    # dny bez otevřeného koše (začátek, přeskočené týdny, konec) = hotovost
    # (po konci smyčky jsou všechny nohy uzavřené ⇒ zbylé dny = hotovost)
    full, d = {}, start
    while d <= end:
        full[d] = curve.get(d, START_EQUITY if ms_of(d) < first_decision else cash)
        d += timedelta(days=1)
    return legs, full, decisions


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


def trade_metrics(legs):
    pnl = [lg["net_pnl"] for lg in legs]
    gains = sum(p for p in pnl if p > 0)
    losses = -sum(p for p in pnl if p < 0)
    top3 = sum(sorted(pnl, reverse=True)[:3])
    return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
            "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
            "net_without_top3": round(sum(pnl) - top3, 4),
            "funding": round(sum(lg["funding"] for lg in legs), 4),
            "costs": round(sum(lg["costs"] for lg in legs), 4),
            "liquidations": sum(lg["liquidated"] for lg in legs),
            "long_net": round(sum(lg["net_pnl"] for lg in legs if lg["side"] == 1), 4),
            "short_net": round(sum(lg["net_pnl"] for lg in legs if lg["side"] == -1), 4)}


def run(market, start, end, mult, W, H, variant, prices=None):
    legs, curve, dec = simulate(market, start, end, W, H, mult, variant, prices)
    cm, rets = curve_metrics(curve, START_EQUITY)
    return {**cm, **trade_metrics(legs), "baskets": sum(1 for x in dec if not x["skipped"]),
            "skipped_weeks": sum(1 for x in dec if x["skipped"]),
            "edge_funding_events_excluded": simulate_edge_events(market, legs)}, legs, rets, curve


def buy_hold(market, start, end, mult, prices=None):
    px = prices or Prices(market)
    c = (FEE + SLIP) * mult
    t0 = ms_of(start)
    share = START_EQUITY / len(ASSETS)
    qty, cash = {}, 0.0
    for a in ASSETS:
        if t0 in market[a]["bars"]:
            qty[a] = share * (1 - c) / px.get(a, t0, 0)
        else:
            cash += share
    curve, d = {}, start
    while d <= end:
        t = ms_of(d) + 23 * HOUR_MS
        curve[d] = cash + sum(q * px.get(a, t, 3) for a, q in qty.items())
        d += timedelta(days=1)
    curve[end] = cash + (curve[end] - cash) * (1 - c)
    cm, rets = curve_metrics(curve, START_EQUITY)
    return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4)}, rets


def simulate_edge_events(market, legs):
    """Info (dodatek 1): funding události přesně v čase vstupu/výstupu nohy — podle protokolu se nezapočítají."""
    return sum((lg["entry_ts"] in market[lg["asset"]]["funding"]) + (lg["exit_ts"] in market[lg["asset"]]["funding"])
               for lg in legs)


def vol_matched(strategy_rets, bh_rets):
    """Info (dodatek 1): B&H přeškálované na stejnou denní volatilitu jako strategie (bez nákladů); kritéria nemění."""
    def sd(x):
        mu = sum(x) / len(x)
        return math.sqrt(sum((r - mu) ** 2 for r in x) / (len(x) - 1))
    k = sd(strategy_rets) / sd(bh_rets) if sd(bh_rets) > 0 else 0.0
    v, peak, mdd = 1.0, 1.0, 0.0
    for r in bh_rets:
        v *= 1 + k * r
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    return {"scale": round(k, 6), "return_pct": round((v - 1) * 100, 4), "max_drawdown_pct": round(mdd * 100, 4)}


def corr(x, y):
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return round(sxy / (sx * sy), 4) if sx > 0 and sy > 0 else None


def btc_daily_returns(market, start, end, prices):
    vals, d = [], start - timedelta(days=1)
    while d <= end:
        vals.append(prices.get("BTCUSDT", ms_of(d) + 23 * HOUR_MS, 3))
        d += timedelta(days=1)
    return [vals[k] / vals[k - 1] - 1 for k in range(1, len(vals))]


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


def neighbors(w, h):
    return [(w2, h2) for (w2, h2) in GRID if (w2 == w) != (h2 == h)]


def pdate(s):
    return date.fromisoformat(s)


def leg_row(period, mult, lg):
    return {"period": period, "variant": lg["period_variant"], "cost_mult": mult, "asset": lg["asset"],
            "side": "LONG" if lg["side"] == 1 else "SHORT", "signal_funding_sum": round(lg["signal"], 8),
            "entry_utc": datetime.fromtimestamp(lg["entry_ts"] / 1000, tz=timezone.utc).isoformat(),
            "exit_utc": datetime.fromtimestamp(lg["exit_ts"] / 1000, tz=timezone.utc).isoformat(),
            "entry": lg["entry"], "exit": lg["exit"], "qty": round(lg["qty"], 10),
            "notional": round(lg["notional"], 6), "gross": round(lg["gross"], 6),
            "funding": round(lg["funding"], 6), "costs": round(lg["costs"], 6),
            "liquidated": lg["liquidated"], "net_pnl": round(lg["net_pnl"], 6)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-fd")
    ap.add_argument("--outdir", default="research/funding_dispersion")
    args = ap.parse_args(argv)
    out = Path(args.outdir)
    market, manifest, missing, fatal = load(args.cache)
    (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
    if fatal:
        print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
        sys.exit(2)
    first_bar = {a: date_of(market[a]["first_bar"]).isoformat() for a in ASSETS}
    first_funding = {a: date_of(market[a]["first_funding"]).isoformat() for a in ASSETS}
    print("DATA_COVERAGE", json.dumps({"first_bar": first_bar, "first_funding": first_funding}))
    px = Prices(market)

    rows, results, tune, rets_store = [], {}, {}, {}
    for (w, h) in GRID:
        tag = vt(w, h)
        results[tag] = {}
        for p, (s, e) in PERIODS.items():
            results[tag][p] = {}
            for m in COST_MULTIPLIERS:
                r, legs, rets, _ = run(market, pdate(s), pdate(e), m, w, h, tag, px)
                results[tag][p][f"x{m}"] = r
                rets_store[(tag, p, m)] = rets
                rows += [leg_row(p, m, lg) for lg in legs]
        tune[tag] = results[tag]["tuning"]["x1"]
    chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
    ctag = vt(*chosen)
    bh, bh_rets = {}, {}
    for p, (s, e) in PERIODS.items():
        bh[p] = {}
        for m in COST_MULTIPLIERS:
            bh[p][f"x{m}"], bh_rets[(p, m)] = buy_hold(market, pdate(s), pdate(e), m, px)
    wf = {}
    for y in WF_YEARS:
        r, legs, _, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag, px)
        wf[str(y)] = r
        rows += [leg_row(f"wf_{y}", 2, lg) for lg in legs]

    res = results[ctag]
    track_a, track_b = evaluate(res, bh)
    passed_a, passed_b = all(track_a.values()), all(track_b.values())
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    dsr = dsr_from_returns(rets_store[(ctag, "validation", 1)], DSR_N, DSR_VAR_ANNUAL / 365)
    nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
    wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
    robust = {"dsr_ge_0_95": dsr["dsr"] >= 0.95, "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
              "walk_forward_ge_3_of_4": wf_pos >= 3}
    s, e = PERIODS["validation"]
    beta_info = {"corr_daily_vs_btc_validation_x1": corr(rets_store[(ctag, "validation", 1)],
                                                         btc_daily_returns(market, pdate(s), pdate(e), px)),
                 "gross_exposure_strategy": 4 * LEG_FRACTION, "gross_exposure_bh": 1.0,
                 "bh_vol_matched_x1": {p: vol_matched(rets_store[(ctag, p, 1)], bh_rets[(p, 1)])
                                       for p in ("validation", "final_test")}}
    verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
    payload = {"protocol": "research/funding_dispersion/PROTOCOL.md", "chosen": ctag,
               "tuning_selection_x1": tune, "strategy": results, "buy_hold_equal_8": bh,
               "walk_forward_x2": wf, "neighbors_val_x2": nb, "track_a": track_a, "track_b": track_b,
               "passed_a": passed_a, "passed_b": passed_b, "dsr_validation_x1": dsr, "robustness": robust,
               "info": {**beta_info, "price_fallbacks": px.fallbacks, "first_bar": first_bar,
                        "first_funding": first_funding},
               "verdict": verdict}
    (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
    with open(out / "trades.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
        w.writeheader()
        w.writerows(rows)
    print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
                                 "robust": robust, "dsr": round(dsr["dsr"], 4), "neighbors": nb,
                                 "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
                                 "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
                                 "wf": {k: v["net_pnl"] for k, v in wf.items()}, **beta_info,
                                 "fallbacks": px.fallbacks}, default=str))


if __name__ == "__main__":
    main()
