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
    """Binance Vision fundingRate: calc_time, funding_interval_hours, last_funding_rate.
    → [(normalizovaný čas vypořádání, sazba, interval_h, surový calc_time)]"""
    out = []
    for r in _csv_rows(payload):
        raw = _ms(int(r[0]))
        out.append((normalize_funding_ts(raw), float(r[2]), float(r[1]), raw))
    return out


def urls(asset):
    base = "https://data.binance.vision/data/futures/um/monthly"
    for y, m in months():
        tag = f"{y}-{m:02d}"
        yield "kl", (y, m), f"{base}/klines/{asset}/1h/{asset}-1h-{tag}.zip"
        yield "fr", (y, m), f"{base}/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"


def add_funding(store, rows, asset, audit):
    """Oprava R1: duplicita po normalizaci se stejnou sazbou = počítat; s jinou sazbou nebo intervalem = chyba."""
    for ts, rate, interval_h, raw in rows:
        if ts in store:
            if store[ts][:2] != (rate, interval_h):
                raise ValueError(f"konfliktní duplicitní funding {asset} {ts}: {store[ts][:2]} vs {(rate, interval_h)}")
            audit["duplicates_same_value"] += 1
            continue
        store[ts] = (rate, interval_h, raw)


def load(cache, fetcher=fetch):
    market, manifest, missing, fatal = {}, [], [], []
    for a in ASSETS:
        bars, fund, present = {}, {}, {"kl": [], "fr": []}
        miss = {"kl": [], "fr": []}
        audit = {"duplicates_same_value": 0}
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
                add_funding(fund, rows, a, audit)
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
        for kind in ("kl", "fr"):
            # povolené jsou jen chybějící měsíce PŘED prvním existujícím (kontrakt ještě neobchodoval)
            if present[kind]:
                first = min(present[kind])
                fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
            else:
                fatal.append({"asset": a, "kind": kind, "month": "all"})
        market[a] = prepare(bars, fund)
        market[a]["load_audit"] = audit
    return market, manifest, missing, fatal


def prepare(bars, fund):
    """bars {ts: (o, h, l, c)}, fund {ts: rate | (rate, interval_h[, raw_ts])} → indexy pro kauzální dotazy.
    Holá sazba (syntetické testy) = interval 8 h, raw = ts."""
    norm = {}
    for ts, v in fund.items():
        if isinstance(v, tuple):
            norm[ts] = (v[0], v[1], v[2] if len(v) > 2 else ts)
        else:
            norm[ts] = (v, 8.0, ts)
    fts = sorted(norm)
    funding = {ts: norm[ts][0] for ts in fts}
    cum = [0.0]
    for ts in fts:
        cum.append(cum[-1] + funding[ts])
    return {"bars": bars, "bts": sorted(bars), "funding": funding, "finterval": {ts: norm[ts][1] for ts in fts},
            "fraw": {ts: norm[ts][2] for ts in fts}, "fts": fts, "fcum": cum,
            "first_bar": min(bars) if bars else None, "first_funding": fts[0] if fts else None}


# ------------------------------------------------------------------ simulace
def ms_of(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def date_of(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def first_monday_on_or_after(d):
    return d + timedelta(days=(7 - d.weekday()) % 7)


FALLBACK_PURPOSES = ("entry", "exit", "funding", "liquidation_check", "mtm", "benchmark")


class Prices:
    def __init__(self, market):
        self.m = market
        self.fallbacks = {p: 0 for p in FALLBACK_PURPOSES}
        self.last_fallback = False

    def get(self, a, t, field, purpose):
        """field: 0 open, 1 high, 2 low, 3 close. Chybí-li svíčka v t: close nejbližší dřívější do 6 h (dodatek 0);
        náhrada se počítá podle účelu (dodatek 2) — je to náhradní ocenění, ne důkaz realizovatelné ceny."""
        self.last_fallback = False
        b = self.m[a]["bars"].get(t)
        if b is not None:
            return b[field]
        for k in range(1, FALLBACK_HOURS + 1):
            b = self.m[a]["bars"].get(t - k * HOUR_MS)
            if b is not None:
                self.fallbacks[purpose] += 1
                self.last_fallback = True
                return b[3]
        raise KeyError(f"chybí cena {a} {datetime.fromtimestamp(t / 1000, tz=timezone.utc)}")


def decision_time(D):
    """Dodatek 2 (D): rozhodnutí až po zveřejnění sazby vypořádané v D (calc_time ≤ D + 1 s podle normalizace)."""
    return D + 1000


def funding_signal(m, D, W):
    """Součet sazeb s časem vypořádání v (D − W dní, D] a surovým calc_time ≤ decision_time(D)."""
    lo = D - W * DAY_MS
    i, j = bisect.bisect_right(m["fts"], lo), bisect.bisect_right(m["fts"], D)
    assert all(m["fraw"][ts] <= decision_time(D) for ts in m["fts"][i:j])
    return m["fcum"][j] - m["fcum"][i]


def funding_chain_gaps(m, lo, hi):
    """Počet nesouvislostí funding řady pokrývající (lo, hi]: chybí předchozí událost ≤ lo, rozestup dvou po sobě
    jdoucích událostí ≠ intervalu (podle intervalu té dřívější), nebo po poslední události ≤ hi chybí další před hi."""
    fts = m["fts"]
    i = bisect.bisect_right(fts, lo) - 1
    if i < 0:
        return None  # kontrakt ještě neměl funding
    gaps, k = 0, i
    while k + 1 < len(fts) and fts[k + 1] <= hi:
        if fts[k + 1] - fts[k] != m["finterval"][fts[k]] * HOUR_MS:
            gaps += 1
        k += 1
    if fts[k] + m["finterval"][fts[k]] * HOUR_MS <= hi and (k + 1 >= len(fts) or fts[k + 1] > hi):
        gaps += 1  # očekávaná událost ≤ hi chybí
    return gaps


def price_gaps(m, lo, hi):
    """Počet chybějících hodinových svíček v [lo, hi]."""
    i, j = bisect.bisect_left(m["bts"], lo), bisect.bisect_right(m["bts"], hi)
    return (hi - lo) // HOUR_MS + 1 - (j - i)


def eligibility(market, a, D, W, entry_ts=None):
    """Způsobilost jen z informací známých v D (dodatek 3): listing, všechny 1h svíčky UZAVŘENÉ do D ([D − W, D − 1 h])
    a souvislá funding řada (D − W, D]. Existence budoucí vstupní svíčky výběr neovlivňuje (kontroluje se až při vstupu).
    Chybějící funding se nikdy nepovažuje za nulový. Vrací (způsobilé, důvod). entry_ts je jen kvůli zpětné kompatibilitě."""
    m = market[a]
    if m["first_funding"] is None or m["first_bar"] is None:
        return False, "no_data"
    lo = D - W * DAY_MS
    if m["first_bar"] > lo or m["first_funding"] > lo:
        return False, "not_listed_for_window"
    if price_gaps(m, lo, D - HOUR_MS):
        return False, "price_gap_in_window"
    g = funding_chain_gaps(m, lo, D)
    if g is None or g > 0:
        return False, "funding_gap_in_window"
    return True, "ok"


def eligible(market, a, D, W, entry_ts):
    return eligibility(market, a, D, W, entry_ts)[0]


def select_legs(signals):
    order = sorted(signals.items(), key=lambda kv: (kv[1], kv[0]))
    longs = [a for a, _ in order[:N_SIDE]]
    shorts = [a for a, _ in order[-N_SIDE:]]
    return longs, shorts


def _liquidate(lg, t, price):
    lg.update(alive=False, liquidated=1, exit_ts=t, exit=price, gross=-lg["notional"])


def simulate(market, start, end, W, H, mult, variant="", prices=None):
    """Vrací (nohy, denní equity {date: value}, rozhodnutí).
    Pořadí v hodině t (vstup ≤ t < výstup): funding události v t (jen t > vstup) → kontrola likvidace short nohy
    podle high svíčky t → ocenění v 23:00. Ve výstupní hodině: je-li open ≥ 2 × vstup ⇒ likvidace gapem (ztráta =
    notional), jinak výstup za open. High po čase výstupu se nepoužívá (oprava R3)."""
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
        why = {a: eligibility(market, a, D, W, entry_ts)[1] for a in ASSETS}
        elig = [a for a in ASSETS if why[a] == "ok"]
        if len(elig) < MIN_ELIGIBLE:
            decisions.append({"decision_utc": datetime.fromtimestamp(decision_time(D) / 1000, tz=timezone.utc).isoformat(),
                              "decision": date_of(D).isoformat(), "skipped": True, "eligible": len(elig),
                              "ineligible_reasons": {a: r for a, r in why.items() if r != "ok"}})
            for k in range(7):
                curve[date_of(D + k * DAY_MS)] = cash
            D += 7 * DAY_MS
            continue
        sig = {a: funding_signal(market[a], D, W) for a in elig}
        longs, shorts = select_legs(sig)
        decisions.append({"decision_utc": datetime.fromtimestamp(decision_time(D) / 1000, tz=timezone.utc).isoformat(),
                          "decision": date_of(D).isoformat(), "skipped": False, "eligible": len(elig),
                          "ineligible_reasons": {a: r for a, r in why.items() if r != "ok"},
                          "longs": longs, "shorts": shorts, "signal": sig})
        equity0 = cash
        open_legs = []
        basket_id = len(decisions)
        decisions[-1]["unfilled_legs"] = []
        for side, names in ((1, longs), (-1, shorts)):
            for a in names:
                if entry_ts not in market[a]["bars"]:
                    # dodatek 3: chybí vstupní svíčka ⇒ noha se neotevře (slot zůstane v hotovosti), žádné přerankování
                    decisions[-1]["unfilled_legs"].append(a)
                    continue
                e = px.get(a, entry_ts, 0, "entry")
                notional = LEG_FRACTION * equity0
                cost_in = notional * c
                cash -= cost_in
                open_legs.append({"period_variant": variant, "basket": basket_id, "asset": a, "side": side,
                                  "entry_ts": entry_ts, "entry": e, "qty": notional / e, "notional": notional,
                                  "costs": cost_in, "funding": 0.0, "liquidated": 0, "alive": True, "signal": sig[a],
                                  "price_fallbacks": 0,
                                  "funding_gaps_in_holding": funding_chain_gaps(market[a], entry_ts, exit_ts - 1) or 0})
        t = entry_ts
        while t < exit_ts:
            for lg in open_legs:
                if not lg["alive"]:
                    continue
                a = lg["asset"]
                if t > entry_ts and t in market[a]["funding"]:
                    amt = -lg["side"] * market[a]["funding"][t] * lg["qty"] * px.get(a, t, 0, "funding")
                    lg["funding"] += amt
                if lg["side"] == -1:
                    hi = px.get(a, t, 1, "liquidation_check")
                    lg["price_fallbacks"] += px.last_fallback
                    if hi >= 2 * lg["entry"]:
                        _liquidate(lg, t, 2 * lg["entry"])
                        cash += lg["gross"] + lg["funding"]
            if (t // HOUR_MS) % 24 == 23:  # close svíčky 23:00 = konec dne
                mtm = sum(lg["side"] * lg["qty"] * (px.get(lg["asset"], t, 3, "mtm") - lg["entry"]) + lg["funding"]
                          for lg in open_legs if lg["alive"])
                curve[date_of(t)] = cash + mtm
            t += HOUR_MS
        for lg in open_legs:
            if lg["alive"]:
                x = px.get(lg["asset"], exit_ts, 0, "exit")
                lg["price_fallbacks"] += px.last_fallback
                if lg["side"] == -1 and x >= 2 * lg["entry"]:  # gap přes likvidační cenu ve výstupní hodině
                    _liquidate(lg, exit_ts, x)
                    cash += lg["gross"] + lg["funding"]
                else:
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
            "edge_funding_events_excluded": simulate_edge_events(market, legs),
            "edge_funding_impact_abs_upper_bound": simulate_edge_events(market, legs, True)[1],
            "legs_with_price_fallback": sum(1 for lg in legs if lg["price_fallbacks"]),
            "legs_with_funding_gap_in_holding": sum(1 for lg in legs if lg["funding_gaps_in_holding"]),
            "per_basket": basket_metrics(legs),
            "unfilled_entry_legs": sum(len(x.get("unfilled_legs", [])) for x in dec)}, legs, rets, curve


def buy_hold(market, start, end, mult, prices=None):
    """Oprava R2: B&H 8 perpů (long 12,5 % na aktivum, 1× bez páky, marže = notional) včetně skutečného fundingu:
    long platí kladnou sazbu z qty × open svíčky v čase události, pro události v (start 00:00, konec dne end).
    Nákup za open první hodiny, prodej za close svíčky 23:00 posledního dne; nedostupné aktivum = hotovost."""
    px = prices or Prices(market)
    c = (FEE + SLIP) * mult
    t0 = ms_of(start)
    t_end = ms_of(end) + 23 * HOUR_MS
    share = START_EQUITY / len(ASSETS)
    qty, cash, funding = {}, 0.0, 0.0
    for a in ASSETS:
        if t0 in market[a]["bars"]:
            qty[a] = share * (1 - c) / px.get(a, t0, 0, "benchmark")
        else:
            cash += share
    events = sorted((t, a) for a in qty for t in market[a]["fts"] if t0 < t <= t_end)
    k, curve, d = 0, {}, start
    while d <= end:
        t = ms_of(d) + 23 * HOUR_MS
        while k < len(events) and events[k][0] <= t:
            te, a = events[k]
            funding -= market[a]["funding"][te] * qty[a] * px.get(a, te, 0, "benchmark")
            k += 1
        curve[d] = cash + funding + sum(q * px.get(a, t, 3, "benchmark") for a, q in qty.items())
        d += timedelta(days=1)
    asset_value = curve[end] - cash - funding
    curve[end] = cash + funding + asset_value * (1 - c)
    cm, rets = curve_metrics(curve, START_EQUITY)
    return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4)}, rets


def simulate_edge_events(market, legs, with_impact=False):
    """Funding události přesně v čase vstupu/výstupu nohy — podle protokolu se nezapočítají (dodatek 1).
    with_impact: (počet, součet |sazba × qty × cena|) = horní mez dopadu na P/L (dodatek 2, E)."""
    n, impact = 0, 0.0
    for lg in legs:
        m = market[lg["asset"]]
        for t, p in ((lg["entry_ts"], lg["entry"]), (lg["exit_ts"], lg["exit"])):
            if t in m["funding"]:
                n += 1
                impact += abs(m["funding"][t] * lg["qty"] * p)
    return (n, round(impact, 6)) if with_impact else n


def basket_metrics(legs):
    """Dodatek 2 (B): metriky z celých košů (4 nohy jednoho rozhodnutí nejsou 4 nezávislá rozhodnutí)."""
    by = {}
    for lg in legs:
        by.setdefault(lg["basket"], []).append(lg)
    pnl = [sum(x["net_pnl"] for x in b) for _, b in sorted(by.items())]
    gains = sum(x for x in pnl if x > 0)
    losses = -sum(x for x in pnl if x < 0)
    return {"baskets": len(pnl), "net_pnl": round(sum(pnl), 4),
            "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
            "net_without_top3": round(sum(pnl) - sum(sorted(pnl, reverse=True)[:3]), 4),
            "baskets_with_price_fallback": sum(1 for _, b in by.items() if any(x["price_fallbacks"] for x in b)),
            "baskets_with_funding_gap": sum(1 for _, b in by.items() if any(x["funding_gaps_in_holding"] for x in b))}


def vol_matched(strategy_rets, bh_rets):
    """Info (dodatek 1): B&H přeškálované na stejnou denní volatilitu jako strategie (bez nákladů); kritéria nemění.
    EX-POST diagnostika (škála z celého období), ne obchodovatelný benchmark (dodatek 2, F)."""
    def sd(x):
        if len(x) < 2:
            return 0.0
        mu = sum(x) / len(x)
        return math.sqrt(sum((r - mu) ** 2 for r in x) / (len(x) - 1))
    k = sd(strategy_rets) / sd(bh_rets) if sd(bh_rets) > 0 else 0.0
    v, peak, mdd = 1.0, 1.0, 0.0
    for r in bh_rets:
        v *= 1 + k * r
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    return {"kind": "ex_post_diagnostic", "scale": round(k, 6), "return_pct": round((v - 1) * 100, 4), "max_drawdown_pct": round(mdd * 100, 4)}


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
        vals.append(prices.get("BTCUSDT", ms_of(d) + 23 * HOUR_MS, 3, "benchmark"))
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


def data_audit(market):
    """Kontrola dat oddělená od výkonnosti (dodatek 3): všechny přechody funding_interval_hours s okolními časy a počet
    nesouladů rozestupu pro dvě možné sémantiky pole — A: interval platí od dané události k další (předpoklad kódu),
    B: interval popisuje úsek končící danou událostí. Sémantiku rozhodne člověk z konkrétních přechodů, ne kód."""
    out = {}
    for a in ASSETS:
        m = market[a]
        fts = m["fts"]
        trans, mis_a, mis_b = [], 0, 0
        for k in range(len(fts) - 1):
            sp = (fts[k + 1] - fts[k]) / HOUR_MS
            ia, ib = m["finterval"][fts[k]], m["finterval"][fts[k + 1]]
            mis_a += sp != ia
            mis_b += sp != ib
            if ia != ib:
                ctx = [(datetime.fromtimestamp(fts[j] / 1000, tz=timezone.utc).isoformat(), m["finterval"][fts[j]])
                       for j in range(max(0, k - 2), min(len(fts), k + 4))]
                trans.append({"at": datetime.fromtimestamp(fts[k + 1] / 1000, tz=timezone.utc).isoformat(),
                              "from_h": ia, "to_h": ib, "spacing_h": sp, "context": ctx})
        out[a] = {"funding_events": len(fts), "interval_transitions": trans,
                  "spacing_mismatch_semantics_A": mis_a, "spacing_mismatch_semantics_B": mis_b,
                  "hour_bars": len(m["bts"]),
                  "missing_hours_since_listing": (price_gaps(m, m["first_bar"], m["bts"][-1]) if m["bts"] else None),
                  "load_audit": m.get("load_audit")}
    return out


def safe_dsr(rets, n, var_annual):
    """Oprava R4: nedefinované DSR (nulový rozptyl, např. žádné obchody) = None + důvod, brána neprošla."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    try:
        return {**dsr_from_returns(rets, n, var_annual / 365), "undefined_reason": None}
    except (ValueError, ZeroDivisionError) as e:
        return {"dsr": None, "undefined_reason": str(e), "n_trials": n, "var_trials": var_annual / 365}


DSR_SENSITIVITY_N = (159, 318, 636)
DSR_SENSITIVITY_V = (0.5, 1.0, 2.0)


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
            "liquidated": lg["liquidated"], "basket": lg["basket"], "price_fallbacks": lg["price_fallbacks"],
            "funding_gaps_in_holding": lg["funding_gaps_in_holding"], "net_pnl": round(lg["net_pnl"], 6)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-fd")
    ap.add_argument("--outdir", default="research/funding_dispersion")
    ap.add_argument("--audit-only", action="store_true", help="jen kontrola dat, bez výpočtu výkonnosti")
    args = ap.parse_args(argv)
    out = Path(args.outdir)
    market, manifest, missing, fatal = load(args.cache)
    (out / "data_source.json").write_text(json.dumps({"archives": manifest, "missing": missing}, indent=1))
    if fatal:
        print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
        sys.exit(2)
    audit = data_audit(market)
    (out / "data_audit.json").write_text(json.dumps(audit, indent=1, default=str))
    print("DATA_AUDIT", json.dumps({a: {k: v for k, v in x.items() if k != "interval_transitions"} | {
        "interval_transitions": len(x["interval_transitions"])} for a, x in audit.items()}, default=str))
    if args.audit_only:
        return
    first_bar = {a: date_of(market[a]["first_bar"]).isoformat() if market[a]["first_bar"] else None for a in ASSETS}
    first_funding = {a: date_of(market[a]["first_funding"]).isoformat() if market[a]["first_funding"] else None
                     for a in ASSETS}
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
    vrets = rets_store[(ctag, "validation", 1)]
    dsr = safe_dsr(vrets, DSR_N, DSR_VAR_ANNUAL)
    dsr_sens = {f"N{n}_V{v}": safe_dsr(vrets, n, v)["dsr"] for n in DSR_SENSITIVITY_N for v in DSR_SENSITIVITY_V}
    nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
    wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
    robust = {"dsr_ge_0_95": dsr["dsr"] is not None and dsr["dsr"] >= 0.95,
              "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
              "walk_forward_ge_3_of_4": wf_pos >= 3}
    s, e = PERIODS["validation"]
    beta_info = {"corr_daily_vs_btc_validation_x1": corr(rets_store[(ctag, "validation", 1)],
                                                         btc_daily_returns(market, pdate(s), pdate(e), px)),
                 "gross_exposure_strategy": 4 * LEG_FRACTION, "gross_exposure_bh": 1.0,
                 "bh_vol_matched_x1": {p: vol_matched(rets_store[(ctag, p, 1)], bh_rets[(p, 1)])
                                       for p in ("validation", "final_test")}}
    verdict = ("KANDIDÁT NA FORWARD PAPER" if (passed_a or passed_b) and all(robust.values()) else "ZAMÍTNUTO")
    flags = {"edge_funding_events": sum(res[p]["x1"]["edge_funding_events_excluded"] for p in PERIODS),
             "unfilled_entry_legs": sum(res[p]["x1"]["unfilled_entry_legs"] for p in PERIODS),
             "legs_with_price_fallback": sum(res[p]["x1"]["legs_with_price_fallback"] for p in PERIODS),
             "legs_with_funding_gap_in_holding": sum(res[p]["x1"]["legs_with_funding_gap_in_holding"] for p in PERIODS)}
    if verdict.startswith("KANDIDÁT") and any(flags.values()):
        verdict = "NEROZHODNUTO — výsledek ovlivněn hranami fundingu / mezerami dat, nutná revize (dodatek 2)"
    payload = {"protocol": "research/funding_dispersion/PROTOCOL.md", "chosen": ctag,
               "tuning_selection_x1": tune, "strategy": results, "buy_hold_equal_8": bh,
               "walk_forward_x2": wf,
               "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-10…2022; pro 2021–22 NE čistý OOS walk-forward", "neighbors_val_x2": nb, "track_a": track_a, "track_b": track_b,
               "passed_a": passed_a, "passed_b": passed_b, "dsr_validation_x1": dsr,
               "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
               "dsr_sensitivity_scenarios": dsr_sens, "robustness": robust, "interpretation_flags": flags,
               "info": {**beta_info, "price_fallbacks_by_purpose": px.fallbacks, "first_bar": first_bar,
                        "first_funding": first_funding,
                        "load_audit": {a: market[a].get("load_audit") for a in ASSETS}},
               "verdict": verdict}
    (out / "results.json").write_text(json.dumps(payload, indent=1, default=str))
    with open(out / "trades.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["period"])
        w.writeheader()
        w.writerows(rows)
    print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
                                 "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "flags": flags,
                                 "neighbors": nb,
                                 "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
                                 "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
                                 "wf": {k: v["net_pnl"] for k, v in wf.items()}, **beta_info,
                                 "fallbacks": px.fallbacks}, default=str))


if __name__ == "__main__":
    main()
