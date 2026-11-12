"""A5 SPOT-LISTING DRIFT — short USDT-M perpu po pozdějším spot listingu (PROTOCOL.md, `1b16021`).
Mechanika (fill, funding, likvidace, equity, metriky) převzata beze změny z A1 PR #39; liší se událost a okna.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.spot_listing_drift.run --cache /tmp/vision-sld --outdir research/spot_listing_drift
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import hashlib
import io
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from bisect import bisect_left, bisect_right
from datetime import date, timedelta
from pathlib import Path

VISION = "https://data.binance.vision/data/futures/um/monthly"
SPOT_VISION = "https://data.binance.vision/data/spot/monthly"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
LISTINGS = Path(__file__).resolve().parent.parent / "new_listing_inventory" / "listings.csv"
UNIVERSE_FROM = date(2020, 2, 1)
END_DAY = date(2026, 10, 31)
FEE, SLIP = 0.00095, 0.0005
COST_MULTIPLIERS = (1, 2, 3)
KS, TS = (1, 3), (10, 30)
GRID = [(k, t) for k in KS for t in TS]
SPOT_TO = date(2026, 9, 30)
PERP_LEAD_DAYS = 7
MIN_EVENTS = 60
WF_MIN_EVENTS = 10
SPLIT = (0.4, 0.3)
SPOT_PREFIXES = ("1000000", "1000", "1M")
START_EQUITY = 10_000.0
NOTIONAL = 100.0
MAX_OPEN = 100
LIQ_MULT = 2.0
SHIFT_DAYS = 3
WINDOW_DAYS = 40
PRE_DAYS = 7
DSR_N, DSR_VAR_ANNUAL = 218, 0.5
DAY_MS = 86_400_000
EPOCH = date(1970, 1, 1)
PLACEBO = "BTCUSDT"


def vt(k, t):
    return f"K{k}_T{t}"


def day_ms(d):
    return (d - EPOCH).days * DAY_MS


def ms_day(ms):
    return EPOCH + timedelta(days=ms // DAY_MS)


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


# ------------------------------------------------------------------ data
def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&%._-~"), headers={"User-Agent": "paper-research/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 451):
                raise
            last = e
        except Exception as e:  # síť: opakovat
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


def _csv_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]


def parse_klines(payload):
    """→ {date: (open, high, low, close, volume)}"""
    return {ms_day(_ms(int(r[0]))): (float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
            for r in _csv_rows(payload)}


def parse_funding(payload):
    return [(_ms(int(r[0])), float(r[2])) for r in _csv_rows(payload)]


def month_range(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def load_perps(path=LISTINGS):
    """→ {symbol: (first_day, last_day)}; jen reused_ticker = False (PROTOCOL)."""
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["reused_ticker"] != "False":
                continue
            out[r["symbol"]] = (date.fromisoformat(r["first_day"]), date.fromisoformat(r["last_day"]))
    return out


def s3_list(prefix, fetcher=fetch):
    """→ (common_prefixes, keys) celého prefixu (stránkování přes marker)."""
    prefixes, keys, marker = [], [], ""
    while True:
        q = {"delimiter": "/", "prefix": prefix}
        if marker:
            q["marker"] = marker
        root = ET.fromstring(fetcher(f"{S3}?{urllib.parse.urlencode(q)}"))
        page_p = [e.findtext(f"{NS}Prefix") for e in root.findall(f"{NS}CommonPrefixes")]
        page_k = [e.findtext(f"{NS}Key") for e in root.findall(f"{NS}Contents")]
        prefixes += page_p
        keys += page_k
        if root.findtext(f"{NS}IsTruncated") != "true":
            return prefixes, keys
        marker = root.findtext(f"{NS}NextMarker") or max(page_p + page_k)


def spot_symbol_for(perp, spot_set):
    if perp in spot_set:
        return perp
    for pre in SPOT_PREFIXES:
        if perp.startswith(pre) and perp[len(pre):] in spot_set:
            return perp[len(pre):]
    return None


def first_volume_day(payload):
    days = sorted(d for d, b in parse_klines(payload).items() if b[4] > 0)
    return days[0] if days else None


def build_events(perps, spot_first):
    """perps {P: (first, last)}, spot_first {P: (spot_symbol, S)} → platné události seřazené podle (S, P)."""
    ev = []
    for p, (spot, S) in spot_first.items():
        if p not in perps or S is None:
            continue
        first, last = perps[p]
        if first <= S - timedelta(days=PERP_LEAD_DAYS) and UNIVERSE_FROM <= S <= SPOT_TO and last >= S:
            ev.append({"symbol": p, "spot": spot, "L": S, "last_day": last, "perp_first": first})
    return sorted(ev, key=lambda x: (x["L"], x["symbol"]))


def split_blocks(events):
    n = len(events)
    a = round(SPLIT[0] * n)
    b = a + round(SPLIT[1] * n)
    return {"tuning": events[:a], "validation": events[a:b], "final_test": events[b:]}


def wf_years(events):
    cnt = {}
    for e in events:
        cnt[e["L"].year] = cnt.get(e["L"].year, 0) + 1
    return sorted(y for y, c in cnt.items() if c >= WF_MIN_EVENTS)


def get_verified(url, cache, fetcher=fetch):
    p = Path(cache) / url.split("/data/", 1)[1]
    if p.exists():
        payload = p.read_bytes()
    else:
        payload = fetcher(url)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    try:
        expected = fetcher(url + ".CHECKSUM").decode().split()[0].lower()
        status = "ok" if expected == sha else "MISMATCH"
    except urllib.error.HTTPError:
        status = "missing"
    return payload, sha, status


def load_symbol(sym, start, end, cache, fetcher=fetch):
    """→ (bars, funding, manifest, missing_months)"""
    bars, fund, manifest, missing = {}, {}, [], []
    for y, m in month_range(start, end):
        tag = f"{y}-{m:02d}"
        for kind, url in (("kl", f"{VISION}/klines/{sym}/1d/{sym}-1d-{tag}.zip"),
                          ("fr", f"{VISION}/fundingRate/{sym}/{sym}-fundingRate-{tag}.zip")):
            try:
                payload, sha, st = get_verified(url, cache, fetcher)
            except urllib.error.HTTPError as e:
                missing.append({"kind": kind, "month": tag, "http": e.code})
                continue
            manifest.append({"url": url, "sha256": sha, "checksum": st})
            if kind == "kl":
                bars.update(parse_klines(payload))
            else:
                for t, rate in parse_funding(payload):
                    fund[t] = rate
    return bars, sorted(fund.items()), manifest, missing


# ------------------------------------------------------------------ series
class Series:
    """Denní svíčky + funding jednoho kontraktu; obchodní den = objem > 0."""

    def __init__(self, bars, funding):
        self.bars = {d: b for d, b in bars.items() if b[4] > 0}
        self.days = sorted(self.bars)
        self.fund = funding
        self.fund_ts = [t for t, _ in funding]

    def trading(self, d):
        return d in self.bars

    def first_trading_in(self, a, b):
        i = bisect_left(self.days, a)
        return self.days[i] if i < len(self.days) and self.days[i] <= b else None

    def last_trading_before(self, d):
        i = bisect_left(self.days, d)
        return self.days[i - 1] if i > 0 else None

    def close_asof(self, d):
        i = bisect_right(self.days, d)
        return self.bars[self.days[i - 1]][3] if i > 0 else None

    def funding_between(self, lo_ms, hi_ms):
        """Události lo_ms < t < hi_ms → [(t, sazba)]"""
        i, j = bisect_right(self.fund_ts, lo_ms), bisect_left(self.fund_ts, hi_ms)
        return self.fund[i:j]

    def px_for_funding(self, t):
        d = ms_day(t)
        b = self.bars.get(d)
        return b[0] if b else self.close_asof(d)


# ------------------------------------------------------------------ plán obchodu (jen kalendář listingu)
def plan(listing, series, k, t):
    """Vstup/výstup podle PROTOCOL. → dict nebo (None, důvod). Používá jen L, data ≤ E pro vstup, ≤ výstup pro výstup."""
    L, last = listing["L"], listing["last_day"]
    E = L + timedelta(days=k)
    if last < E:
        return None, "delist_before_entry"
    e = series.first_trading_in(E, min(E + timedelta(days=SHIFT_DAYS), last))
    if e is None:
        return None, "no_entry_bar"
    X = L + timedelta(days=t)
    if last < X:
        return {"entry": e, "exit_day": last, "exit_kind": "close_forced_delist"}, None
    x = series.first_trading_in(X, X + timedelta(days=SHIFT_DAYS))
    if x is not None:
        return {"entry": e, "exit_day": x, "exit_kind": "open"}, None
    xb = series.last_trading_before(X)
    return {"entry": e, "exit_day": xb, "exit_kind": "close_fallback"}, None


def end_ordinal(p):
    """Den, od kterého pozice neblokuje kapacitu (výstup za open uvolní slot týž den)."""
    return p["exit_day"] if p["exit_kind"] == "open" else p["exit_day"] + timedelta(days=1)


# ------------------------------------------------------------------ simulace jedné short pozice
def simulate_short(series, entry, exit_day, exit_kind, mult):
    o = series.bars[entry][0]
    fill = o * (1 - SLIP * mult)  # prodej
    qty = NOTIONAL / fill
    fee_in = NOTIONAL * FEE * mult
    last_liq_day = exit_day - timedelta(days=1) if exit_kind == "open" else exit_day
    d, liq = entry, None
    while d <= last_liq_day:
        b = series.bars.get(d)
        if b is not None and b[1] >= LIQ_MULT * fill:
            liq = d
            break
        d += timedelta(days=1)
    lo = day_ms(entry)
    if liq is not None:
        hi = day_ms(liq)
        funding = sum(rate * qty * series.px_for_funding(ts) for ts, rate in series.funding_between(lo, hi))
        return {"exit_day": liq, "exit_kind": "liquidation", "entry_fill": fill, "exit_fill": LIQ_MULT * fill,
                "qty": qty, "fees": fee_in, "fee_in": fee_in, "funding": funding, "price_pnl": -NOTIONAL,
                "net_pnl": -NOTIONAL - fee_in + funding, "gross_ret": -1.0, "hi_ms": hi}
    px = series.bars[exit_day][0] if exit_kind == "open" else series.bars[exit_day][3]
    hi = day_ms(exit_day) if exit_kind == "open" else day_ms(exit_day) + DAY_MS
    xfill = px * (1 + SLIP * mult)  # zpětný nákup
    fee_out = qty * xfill * FEE * mult
    funding = sum(rate * qty * series.px_for_funding(ts) for ts, rate in series.funding_between(lo, hi))
    price_pnl = qty * (fill - xfill)
    return {"exit_day": exit_day, "exit_kind": exit_kind, "entry_fill": fill, "exit_fill": xfill, "qty": qty,
            "fees": fee_in + fee_out, "fee_in": fee_in, "funding": funding, "price_pnl": price_pnl,
            "net_pnl": price_pnl - fee_in - fee_out + funding, "gross_ret": (o - px) / o, "hi_ms": hi}


# ------------------------------------------------------------------ portfolio bloku
def schedule(events, data, k, t):
    """Plány vstupů událostí bloku po aplikaci kapacity. → (plány, počty důvodů)."""
    reasons, cands = {}, []
    for li in events:
        s = data.get(li["symbol"])
        if s is None:
            reasons["excluded_data"] = reasons.get("excluded_data", 0) + 1
            continue
        p, why = plan(li, s, k, t)
        if p is None:
            reasons[why] = reasons.get(why, 0) + 1
            continue
        cands.append({**p, "symbol": li["symbol"], "L": li["L"]})
    cands.sort(key=lambda p: (p["entry"], p["symbol"]))
    accepted = []
    for p in cands:
        n_open = sum(1 for q in accepted if q["entry"] <= p["entry"] < end_ordinal(q))
        if n_open >= MAX_OPEN:
            reasons["skipped_capacity"] = reasons.get("skipped_capacity", 0) + 1
            continue
        accepted.append(p)
    return accepted, reasons


def run_block(plans, data, mult, placebo=None):
    """→ (trades, equity[(date, value)]). placebo = Series BTC ⇒ stejný rozvrh, short BTC."""
    trades = []
    for p in plans:
        s = placebo if placebo is not None else data[p["symbol"]]
        if placebo is not None:
            # stejné dny; chybí-li BTC svíčka (nemělo by), posun jako u listingu
            entry = placebo.first_trading_in(p["entry"], p["entry"] + timedelta(days=SHIFT_DAYS))
            if p["exit_kind"] == "open":
                xd = placebo.first_trading_in(p["exit_day"], p["exit_day"] + timedelta(days=SHIFT_DAYS))
            else:
                xd = p["exit_day"] if placebo.trading(p["exit_day"]) else placebo.last_trading_before(p["exit_day"])
            r = simulate_short(placebo, entry, xd, p["exit_kind"], mult)
        else:
            r = simulate_short(s, p["entry"], p["exit_day"], p["exit_kind"], mult)
        trades.append({"symbol": p["symbol"], "L": p["L"], "entry_day": p["entry"], **r})
    return trades, equity_curve(trades, data, placebo)


def equity_curve(trades, data, placebo=None):
    """Denní equity za close: 10 000 + realizované (od dne výstupu) + neuzavřené (qty·(fill − close) − vstupní poplatek
    + funding s t < konec dne a t < hi_ms)."""
    if not trades:
        return []
    start = min(tr["entry_day"] for tr in trades) - timedelta(days=1)
    end = max(tr["exit_day"] for tr in trades)
    n = (end - start).days + 1
    realized = [0.0] * (n + 1)
    openv = [0.0] * n
    for tr in trades:
        realized[(tr["exit_day"] - start).days] += tr["net_pnl"]
        s = placebo if placebo is not None else data[tr["symbol"]]
        ev = s.funding_between(day_ms(tr["entry_day"]), tr["hi_ms"])
        j, f = 0, 0.0
        d = tr["entry_day"]
        while d < tr["exit_day"]:
            cut = day_ms(d) + DAY_MS
            while j < len(ev) and ev[j][0] < cut:
                f += ev[j][1] * tr["qty"] * s.px_for_funding(ev[j][0])
                j += 1
            openv[(d - start).days] += tr["qty"] * (tr["entry_fill"] - s.close_asof(d)) - tr["fee_in"] + f
            d += timedelta(days=1)
    out, cum = [], 0.0
    for i in range(n):
        cum += realized[i]
        out.append((start + timedelta(days=i), START_EQUITY + cum + openv[i]))
    return out


# ------------------------------------------------------------------ metriky
def daily_returns(curve):
    v = [x for _, x in curve]
    return [b / a - 1 for a, b in zip(v, v[1:]) if a > 0]


def sharpe(rets):
    if len(rets) < 2:
        return 0.0
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))
    return m / sd * math.sqrt(365) if sd > 0 else 0.0


def max_dd(curve):
    peak, dd = -1e18, 0.0
    for _, v in curve:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak if peak > 0 else 0.0)
    return dd


def summarize(trades, curve):
    pnl = [tr["net_pnl"] for tr in trades]
    pos, neg = sum(x for x in pnl if x > 0), -sum(x for x in pnl if x < 0)
    srt = sorted(pnl, reverse=True)
    net = sum(pnl)
    return {"trades": len(pnl), "net_pnl": round(net, 4), "net_pct": round(net / START_EQUITY * 100, 4),
            "pf": round(pos / neg, 4) if neg > 0 else None,
            "net_ex_top3": round(sum(srt[3:]), 4),
            "top5_share": round(sum(srt[:5]) / net, 4) if net > 0 else None,
            "win_rate": round(sum(1 for x in pnl if x > 0) / len(pnl), 4) if pnl else None,
            "gross_edge_mean": round(sum(tr["gross_ret"] for tr in trades) / len(trades), 6) if trades else None,
            "funding_sum": round(sum(tr["funding"] for tr in trades), 4),
            "fees_sum": round(sum(tr["fees"] for tr in trades), 4),
            "liquidations": sum(1 for tr in trades if tr["exit_kind"] == "liquidation"),
            "forced_delist": sum(1 for tr in trades if tr["exit_kind"] == "close_forced_delist"),
            "sharpe": round(sharpe(daily_returns(curve)), 4), "max_dd": round(max_dd(curve), 4),
            "start": curve[0][0].isoformat() if curve else None, "end": curve[-1][0].isoformat() if curve else None}


def bh_btc(btc, start, end):
    if start is None:
        return None
    s, e = date.fromisoformat(start) + timedelta(days=1), date.fromisoformat(end)
    d0 = btc.first_trading_in(s, s + timedelta(days=SHIFT_DAYS))
    o = btc.bars[d0][0]
    curve, d = [(d0 - timedelta(days=1), START_EQUITY)], d0
    while d <= e:
        curve.append((d, START_EQUITY * btc.close_asof(d) / o))
        d += timedelta(days=1)
    return {"net_pct": round((curve[-1][1] / START_EQUITY - 1) * 100, 4),
            "sharpe": round(sharpe(daily_returns(curve)), 4), "max_dd": round(max_dd(curve), 4)}


# ------------------------------------------------------------------ hlavní běh
def run_all(events, data, btc):
    res = {"variants": {}, "reasons": {}}
    rows = []
    blocks = split_blocks(events)
    years = wf_years(events)
    res["wf_years"] = years
    all_blocks = list(blocks.items()) + [(f"wf{y}", [e for e in events if e["L"].year == y]) for y in years]
    for k, t in GRID:
        v = vt(k, t)
        res["variants"][v] = {}
        for bname, evs in all_blocks:
            plans, reasons = schedule(evs, data, k, t)
            res["reasons"][f"{v}/{bname}"] = reasons
            for mult in COST_MULTIPLIERS:
                if bname.startswith("wf") and mult != 2:
                    continue
                key = f"{bname}_x{mult}"
                tr, cv = run_block(plans, data, mult)
                ptr, pcv = run_block(plans, data, mult, placebo=btc)
                sm = summarize(tr, cv)
                res["variants"][v][key] = {"strategy": sm, "placebo_btc_short": summarize(ptr, pcv),
                                          "bh_btc": bh_btc(btc, sm["start"], sm["end"]),
                                          "_curve": cv}
                for kind, ts in (("strategy", tr), ("placebo", ptr)):
                    for x in ts:
                        rows.append({"variant": v, "block": bname, "mult": mult, "kind": kind, "symbol": x["symbol"],
                                     "spot_listing_day": x["L"].isoformat(), "entry_day": x["entry_day"].isoformat(),
                                     "exit_day": x["exit_day"].isoformat(), "exit_kind": x["exit_kind"],
                                     "entry_fill": f"{x['entry_fill']:.10g}", "exit_fill": f"{x['exit_fill']:.10g}",
                                     "qty": f"{x['qty']:.10g}", "fees": f"{x['fees']:.6f}", "funding": f"{x['funding']:.6f}",
                                     "gross_ret": f"{x['gross_ret']:.6f}", "net_pnl": f"{x['net_pnl']:.6f}"})
    return res, rows


def evaluate(res):
    tun = {v: res["variants"][v]["tuning_x1"]["strategy"]["net_pnl"] for v in res["variants"]}
    order = [vt(k, t) for k, t in GRID]
    best = max(order, key=lambda v: (tun[v], -order.index(v)))
    V = res["variants"][best]
    g = lambda b: V[b]["strategy"]
    pl = lambda b: V[b]["placebo_btc_short"]
    bh = V["validation_x1"]["bh_btc"]
    rt_cost = 2 * (FEE + SLIP)
    k, t = map(int, best[1:].split("_T"))
    neigh = [vt(kk, t) for kk in KS if kk != k] + [vt(k, tt) for tt in TS if tt != t]
    crit = {
        "C1_val_x2_net_gt0_pf_gt1_2": g("validation_x2")["net_pnl"] > 0 and (g("validation_x2")["pf"] or 0) > 1.2,
        "C2_val_x2_gt_placebo": g("validation_x2")["net_pnl"] > pl("validation_x2")["net_pnl"],
        "C3_val_x1_ex_top3_gt0": g("validation_x1")["net_ex_top3"] > 0,
        "C4_val_x1_sharpe_dd_vs_bh": bool(bh) and g("validation_x1")["sharpe"] > bh["sharpe"] and g("validation_x1")["max_dd"] <= bh["max_dd"],
        "C5_final_x2_gt0_and_placebo": g("final_test_x2")["net_pnl"] > 0 and g("final_test_x2")["net_pnl"] > pl("final_test_x2")["net_pnl"],
        "C6_val_trades_ge30": g("validation_x1")["trades"] >= 30,
        "C7_tuning_gross_edge_ge_3x_cost": (g("tuning_x1")["gross_edge_mean"] or 0) >= 3 * rt_cost,
    }
    from tools.research.deflated_sharpe import dsr_from_returns
    dsr = dsr_from_returns(daily_returns(V["validation_x1"]["_curve"]), DSR_N, DSR_VAR_ANNUAL / 365)
    wf = {y: V[f"wf{y}_x2"]["strategy"]["net_pnl"] for y in res["wf_years"]}
    robust = {"dsr_ge_0_95": dsr["dsr"] >= 0.95,
              "neighbours_val_x2_gt0": all(res["variants"][n]["validation_x2"]["strategy"]["net_pnl"] > 0 for n in neigh),
              "walk_forward_ge_2_3_years": bool(wf) and sum(1 for x in wf.values() if x > 0) >= 2 / 3 * len(wf)}
    passed = all(crit.values()) and all(robust.values())
    return {"selected": best, "tuning_x1_net_by_variant": tun, "criteria": crit, "robustness": robust,
            "neighbours": neigh, "walk_forward_x2": wf, "dsr_validation_x1": dsr,
            "verdict": "kandidat_forward_paper" if passed else "zamitnuto"}


def write_outputs(outdir, res, ev, rows, meta):
    out = Path(outdir)
    with open(out / "trades.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys()) if rows else ["variant"])
        w.writeheader()
        w.writerows(rows)
    clean = {v: {b: {kk: vv for kk, vv in x.items() if kk != "_curve"} for b, x in bl.items()} for v, bl in res["variants"].items()}
    js = {"protocol": "research/spot_listing_drift/PROTOCOL.md (1b16021)", **meta, "evaluation": ev,
          "variants": clean, "plan_reasons": res["reasons"]}
    (out / "results.json").write_text(json.dumps(js, indent=1, ensure_ascii=False, default=str))
    S = clean[ev["selected"]]
    L = [f"# A5 SPOT-LISTING DRIFT — výsledky (PAPER výzkum, ne doporučení)", "",
         f"Bloky (S): " + ", ".join(f"{k} {v}" for k, v in meta["block_bounds"].items()), "",
         f"Protokol `1b16021`. Zvolená varianta (ladění ×1): **{ev['selected']}**. Verdikt: **{ev['verdict']}**.", "",
         "| blok | náklady | obchody | čistý P/L | PF | Sharpe | max DD | placebo BTC short | B&H BTC % (Sharpe, DD) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for b in ("tuning", "validation", "final_test"):
        for m in COST_MULTIPLIERS:
            x = S[f"{b}_x{m}"]
            s, p, h = x["strategy"], x["placebo_btc_short"], x["bh_btc"] or {}
            L.append(f"| {b} | ×{m} | {s['trades']} | {s['net_pnl']:+.2f} ({s['net_pct']:+.2f} %) | {s['pf']} | {s['sharpe']} | "
                     f"{s['max_dd']:.1%} | {p['net_pnl']:+.2f} | {h.get('net_pct')} ({h.get('sharpe')}, {h.get('max_dd')}) |")
    L += ["", "Ladění ×1 podle varianty: " + ", ".join(f"{k} {v:+.2f}" for k, v in ev["tuning_x1_net_by_variant"].items()),
          "", "Kritéria: " + ", ".join(f"{k} {'✔' if v else '✘'}" for k, v in ev["criteria"].items()),
          "", "Robustnost: " + ", ".join(f"{k} {'✔' if v else '✘'}" for k, v in ev["robustness"].items()),
          f"; DSR {ev['dsr_validation_x1']['dsr']:.3f} (N = {DSR_N}); WF ×2 " + ", ".join(f"{y} {v:+.2f}" for y, v in ev["walk_forward_x2"].items()),
          "", f"Data: {meta['archives']} archivů, checksumy {meta['checksums']}; {meta['universe']} událostí, "
          f"vyřazeno pro data {meta['excluded_data']}.", ""]
    (out / "RESULTS.md").write_text("\n".join(L))


def discover_spot(perps, cache, workers):
    """→ ({perp: (spot_symbol, S)}, manifest, info). S = první den s objemem > 0 v nejstarších spot 1d archivech."""
    prefixes, _ = s3_list("data/spot/monthly/klines/")
    spot_set = {p.rstrip("/").rsplit("/", 1)[1] for p in prefixes}
    cand = {p: spot_symbol_for(p, spot_set) for p in perps}
    cand = {p: sp for p, sp in cand.items() if sp}
    manifest, out = [], {}

    def one(item):
        p, sp = item
        _, keys = s3_list(f"data/spot/monthly/klines/{sp}/1d/")
        zips = sorted(k for k in keys if k.endswith(".zip"))
        man = []
        for k in zips[:3]:
            payload, sha, st = get_verified(f"https://data.binance.vision/{k}", cache)
            man.append({"url": f"https://data.binance.vision/{k}", "sha256": sha, "checksum": st})
            d = first_volume_day(payload)
            if d is not None:
                return p, sp, d, man
        return p, sp, None, man

    with cf.ThreadPoolExecutor(workers) as ex:
        for p, sp, d, man in ex.map(one, sorted(cand.items())):
            manifest += man
            out[p] = (sp, d)
    return out, manifest, {"spot_symbols": len(spot_set), "perps_with_spot": len(cand)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    t0 = time.time()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    perps = load_perps()
    spot_first, manifest, dinfo = discover_spot(perps, a.cache, a.workers)
    events = build_events(perps, spot_first)
    with open(out / "events.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["spot_listing_day", "perp", "spot", "perp_first_day", "perp_last_day"])
        for e in events:
            w.writerow([e["L"], e["symbol"], e["spot"], e["perp_first"], e["last_day"]])
    print(f"events {len(events)} {dinfo} {time.time() - t0:.0f}s", flush=True)
    if len(events) < MIN_EVENTS:
        (out / "results.json").write_text(json.dumps({"verdict": "DATA_NO_GO", "events": len(events), **dinfo}, indent=1))
        print("A5_SUMMARY " + json.dumps({"verdict": "DATA_NO_GO", "events": len(events)}), flush=True)
        return

    def work(li):
        end = min(li["L"] + timedelta(days=WINDOW_DAYS), END_DAY, li["last_day"])
        return li, load_symbol(li["symbol"], li["L"] - timedelta(days=PRE_DAYS), end, a.cache)

    data, excluded = {}, []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, (li, (bars, fund, man, miss)) in enumerate(ex.map(work, events), 1):
            manifest += man
            if miss:
                excluded.append({"symbol": li["symbol"], "missing": miss})
            else:
                data[li["symbol"]] = Series(bars, fund)
            if i % 50 == 0:
                print(f"{i}/{len(events)} {time.time() - t0:.0f}s", flush=True)
    bb, bf, bm, bmiss = load_symbol(PLACEBO, date(2020, 1, 1), END_DAY, a.cache)
    manifest += bm
    if bmiss:
        raise SystemExit(f"FATAL: chybí BTC archivy {bmiss}")
    btc = Series(bb, bf)
    cs = {}
    for m in manifest:
        cs[m["checksum"]] = cs.get(m["checksum"], 0) + 1
    if cs.get("MISMATCH"):
        raise SystemExit(f"FATAL: neshoda checksumu {cs}")
    if len(excluded) > 0.02 * len(events):
        raise SystemExit(f"FATAL: vyřazeno {len(excluded)}/{len(events)} > 2 %")
    # informačně: náběh S−7 → open S (jen popis)
    runup = []
    for e in events:
        s = data.get(e["symbol"])
        if s is None:
            continue
        a0 = s.first_trading_in(e["L"] - timedelta(days=PRE_DAYS), e["L"])
        if a0 is not None and e["L"] in s.bars and a0 < e["L"]:
            runup.append(s.bars[e["L"]][0] / s.bars[a0][0] - 1)
    res, rows = run_all(events, data, btc)
    ev = evaluate(res)
    bl = split_blocks(events)
    meta = {"universe": len(events), "excluded_data": len(excluded), "excluded_detail": excluded,
            "archives": len(manifest), "checksums": cs, "runtime_s": round(time.time() - t0), **dinfo,
            "block_bounds": {k: f"{v[0]['L']}…{v[-1]['L']} ({len(v)})" for k, v in bl.items() if v},
            "wf_years": res["wf_years"],
            "info_runup_pre7_to_S_open": {"n": len(runup), "mean": round(sum(runup) / len(runup), 4) if runup else None,
                                          "median": round(sorted(runup)[len(runup) // 2], 4) if runup else None}}
    (out / "data_source.json").write_text(json.dumps({"source": [VISION, SPOT_VISION], "archives": manifest}, indent=1))
    write_outputs(a.outdir, res, ev, rows, meta)
    S = res["variants"][ev["selected"]]
    print("A5_SUMMARY " + json.dumps({"selected": ev["selected"], "verdict": ev["verdict"], "events": len(events),
                                      "blocks": meta["block_bounds"],
                                      "tun_gross": S["tuning_x1"]["strategy"]["gross_edge_mean"],
                                      "val_x2": S["validation_x2"]["strategy"]["net_pnl"],
                                      "val_x2_placebo": S["validation_x2"]["placebo_btc_short"]["net_pnl"],
                                      "final_x2": S["final_test_x2"]["strategy"]["net_pnl"],
                                      "dsr": ev["dsr_validation_x1"]["dsr"], "criteria": ev["criteria"],
                                      "robust": ev["robustness"], "runup": meta["info_runup_pre7_to_S_open"]}, default=str), flush=True)


if __name__ == "__main__":
    main()
