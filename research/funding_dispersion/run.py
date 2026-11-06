"""Průřezová disperze fundingu, koš 8 USDT-M perpů (H-20261106-2) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.funding_dispersion.run --cache /tmp/vision-fd --outdir research/funding_dispersion
"""
import argparse
import ast
import bisect
import fcntl
import csv
import hashlib
import io
import json
import math
import os
import sys
import uuid
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


def spacing_ok(prev_ts, prev_iv, ts, iv):
    """Sémantika B (rozhodnutí z data_audit.json, viz FUNDING_SEMANTICS.json): `funding_interval_hours` záznamu = nastavení
    platné v okamžiku jeho vypořádání, tj. délka úseku KONČÍCÍHO touto událostí. Při změně nastavení uprostřed úseku smí
    rozestup odpovídat intervalu kterékoli ze dvou sousedních událostí (SOLUSDT 2022-11-10 00:00 → 04:00)."""
    sp = ts - prev_ts
    return sp == iv * HOUR_MS or (iv != prev_iv and sp == prev_iv * HOUR_MS)


def funding_chain_gaps(m, lo, hi):
    """Počet nesouvislostí funding řady pokrývající (lo, hi] podle sémantiky B: chybí předchozí událost ≤ lo (None),
    rozestup sousedních událostí neodpovídá (spacing_ok), nebo po poslední události ≤ hi chybí další, očekávaná
    nejpozději za interval poslední události (konzervativní: změna nastavení po ní se může projevit jako mezera)."""
    fts = m["fts"]
    i = bisect.bisect_right(fts, lo) - 1
    if i < 0:
        return None  # kontrakt ještě neměl funding
    gaps, k = 0, i
    while k + 1 < len(fts) and fts[k + 1] <= hi:
        if not spacing_ok(fts[k], m["finterval"][fts[k]], fts[k + 1], m["finterval"][fts[k + 1]]):
            gaps += 1
        k += 1
    if fts[k] + m["finterval"][fts[k]] * HOUR_MS <= hi:
        gaps += 1  # očekávaná událost ≤ hi chybí
    return gaps


def funding_window(m, entry, exit_):
    """Jediná konvence hranic držení pro účtování i kontrolu úplnosti (kolo 6, bod 2): události s entry < t < exit.
    Událost přesně ve vstupu ani ve výstupu se neúčtuje. Vrací seřazený seznam časů událostí v řadě."""
    fts = m["fts"]
    return fts[bisect.bisect_right(fts, entry):bisect.bisect_left(fts, exit_)]


def funding_completeness(m, entry, exit_):
    """Úplnost fundingu pro držení (entry, exit) — tytéž hranice jako funding_window (kolo 6, body 1 a 2).
    Tři oddělené veličiny: nesouvislosti (= funding_chain_gaps na (entry, exit − 1]), odhad chybějících událostí
    a neznámé pokrytí (před vstupem žádná událost ⇒ prefix nelze ověřit). Chybějící sazba se nikdy nedosadí nulou."""
    if exit_ <= entry:  # kolo 8: prázdné držení nemá co pokrýt (dřív mohlo hlásit mezeru)
        return {"discontinuities": 0, "missing_events": 0, "unknown_coverage": False}
    hi = exit_ - 1
    disc = funding_chain_gaps(m, entry, hi)
    if disc is None:
        return {"discontinuities": 0, "missing_events": 0, "unknown_coverage": True}
    fts, iv = m["fts"], m["finterval"]
    k = bisect.bisect_right(fts, entry) - 1
    missing = 0
    while k + 1 < len(fts) and fts[k + 1] <= hi:
        if not spacing_ok(fts[k], iv[fts[k]], fts[k + 1], iv[fts[k + 1]]):
            step = iv[fts[k + 1]] * HOUR_MS  # sémantika B: interval pozdější události = úsek končící jí
            missing += max(1, -(-(fts[k + 1] - fts[k]) // step) - 1)
        k += 1
    step = iv[fts[k]] * HOUR_MS
    if fts[k] + step <= hi:
        missing += (hi - fts[k]) // step  # chybějící konec řady
    return {"discontinuities": disc, "missing_events": int(missing), "unknown_coverage": False}


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


def _holding_gaps(m, entry, exit_):
    """Nesouvislosti fundingu v držení; neznámé pokrytí se počítá jako závada (dřív `None or 0` ⇒ 0)."""
    c = funding_completeness(m, entry, exit_)
    return c["discontinuities"] + int(c["unknown_coverage"])


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
        decisions[-1]["unfilled_entries"] = []
        for side, names in ((1, longs), (-1, shorts)):
            for a in names:
                if entry_ts not in market[a]["bars"]:
                    # dodatek 3: chybí vstupní svíčka ⇒ noha se neotevře (slot zůstane v hotovosti), žádné přerankování.
                    # Kolo 6, bod 4: auditní záznam bez fiktivní pozice, poplatku či cooldownu; notional ze známé equity.
                    decisions[-1]["unfilled_legs"].append(a)
                    decisions[-1]["unfilled_entries"].append({
                        "asset": a, "side": side, "entry_utc": datetime.fromtimestamp(entry_ts / 1000, tz=timezone.utc).isoformat(),
                        "planned_notional": round(LEG_FRACTION * equity0, 6), "reason": "missing_entry_bar"})
                    continue
                e = px.get(a, entry_ts, 0, "entry")
                notional = LEG_FRACTION * equity0
                cost_in = notional * c
                cash -= cost_in
                open_legs.append({"period_variant": variant, "basket": basket_id, "asset": a, "side": side,
                                  "entry_ts": entry_ts, "entry": e, "qty": notional / e, "notional": notional,
                                  "costs": cost_in, "funding": 0.0, "liquidated": 0, "alive": True, "signal": sig[a],
                                  "price_fallbacks": 0,
                                  "fwin": set(funding_window(market[a], entry_ts, exit_ts)),
                                  "funding_gaps_in_holding": _holding_gaps(market[a], entry_ts, exit_ts)})
        t = entry_ts
        while t < exit_ts:
            for lg in open_legs:
                if not lg["alive"]:
                    continue
                a = lg["asset"]
                if t in lg["fwin"]:
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
            lg.pop("fwin", None)
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
            "unfilled_entry_legs": sum(len(x.get("unfilled_legs", [])) for x in dec),
            "unfilled_entries": [e for x in dec for e in x.get("unfilled_entries", [])]}, legs, rets, curve


def buy_hold(market, start, end, mult, prices=None):
    """Oprava R2: B&H 8 perpů (long 12,5 % na aktivum, 1× bez páky, marže = notional) včetně skutečného fundingu:
    long platí kladnou sazbu z qty × open svíčky v čase události, pro události v (start 00:00, konec dne end).
    Nákup za open první hodiny, prodej za close svíčky 23:00 posledního dne; nedostupné aktivum = hotovost.
    Kolo 6, body 1–3: držení aktiva = (t0, prodej) s prodejem za close 23:00 posledního dne, tj. v čase konce dne;
    funding podle funding_window (stejné hranice jako strategie) a úplnost řady podle funding_completeness pro
    každé skutečně držené aktivum. Datové závady benchmarku (mezery fundingu, neznámé pokrytí, náhradní ceny,
    nedostupnost na začátku) se vrací jako počty — o blokaci rozhoduje registr DATA_DEFECTS."""
    px = prices or Prices(market)
    c = (FEE + SLIP) * mult
    t0 = ms_of(start)
    exit_ = ms_of(end) + DAY_MS  # close svíčky 23:00 posledního dne
    share = START_EQUITY / len(ASSETS)
    qty, cash, funding, fallbacks, unavailable = {}, 0.0, 0.0, 0, []

    def price(a, t, field):
        nonlocal fallbacks
        p = px.get(a, t, field, "benchmark")
        fallbacks += px.last_fallback
        return p

    for a in ASSETS:
        if t0 in market[a]["bars"]:
            qty[a] = share * (1 - c) / price(a, t0, 0)
        else:
            cash += share
            unavailable.append(a)
    completeness = {a: funding_completeness(market[a], t0, exit_) for a in qty}
    events = sorted((t, a) for a in qty for t in funding_window(market[a], t0, exit_))
    k, curve, d = 0, {}, start
    while d <= end:
        t = ms_of(d) + 23 * HOUR_MS
        while k < len(events) and events[k][0] <= t:
            te, a = events[k]
            funding -= market[a]["funding"][te] * qty[a] * price(a, te, 0)
            k += 1
        curve[d] = cash + funding + sum(q * price(a, t, 3) for a, q in qty.items())
        d += timedelta(days=1)
    asset_value = curve[end] - cash - funding
    curve[end] = cash + funding + asset_value * (1 - c)
    cm, rets = curve_metrics(curve, START_EQUITY)
    return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4),
            "funding_completeness": completeness,
            "funding_missing_events": sum(x["missing_events"] for x in completeness.values()),
            "funding_discontinuities": sum(x["discontinuities"] for x in completeness.values()),
            "funding_unknown_coverage_assets": sum(x["unknown_coverage"] for x in completeness.values()),
            "price_fallbacks": fallbacks, "unavailable_at_start": unavailable}, rets


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


IMPLEMENTED_SEMANTICS = "B"  # spacing_ok: interval záznamu = úsek končící událostí, tolerance při změně nastavení
SEMANTICS_FILE = "FUNDING_SEMANTICS.json"
AUDIT_MANIFEST_FILE = "audit_manifest.json"
PERFORMANCE_FILES = ("results.json", "trades.csv")
# Funkce, které implementují rozhodnutou sémantiku a hranice fundingu; jejich zdroj tvoří otisk implementace (kolo 6, bod 5).
# Kolo 8, bod 2: otisk CELÉ implementace, na níž závisí ekonomický výsledek a verdikt — tento soubor (simulace, benchmark,
# funding, náklady, equity, vstupy/výstupy, brány, registr, verdikt, konstanty) a modul DSR. Počítá se z AST bez docstringů
# a komentářů: změna kódu nebo konstanty otisk změní, změna komentáře/docstringu ne. Součástí je verze Pythonu (major.minor),
# protože tvar AST se mezi verzemi může lišit — jiná verze ⇒ jiný otisk ⇒ konzervativně odmítnuto.
FINGERPRINT_SOURCES = ("research/funding_dispersion/run.py", "tools/research/deflated_sharpe.py")
REQUIRED_DECISION_FIELDS = ("semantics", "evidence", "decided_utc", "audit_id", "impl_sha256", "data_manifest_sha256")


def _strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body \
                and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    return tree


def code_fingerprint(sources):
    """sources {relativní cesta: text} → sha256 normalizovaného AST (deterministické pořadí podle cesty)."""
    h = hashlib.sha256(f"python{sys.version_info[0]}.{sys.version_info[1]}".encode())
    for name in sorted(sources):
        tree = _strip_docstrings(ast.parse(sources[name]))
        h.update(name.encode() + b"\0" + ast.dump(tree, include_attributes=False).encode() + b"\0")
    return h.hexdigest()


def impl_fingerprint():
    root = Path(__file__).resolve().parents[2]
    return code_fingerprint({rel: (root / rel).read_text() for rel in FINGERPRINT_SOURCES})


def manifest_fingerprint(manifest, missing=()):
    """sha256 skutečně načtených dat: seřazené (url, sha256 archivu) + seřazené chybějící url. Nezávisí na pořadí stahování."""
    rows = sorted((x["url"], x["sha256"]) for x in manifest)
    gone = sorted(x["url"] for x in missing)
    return hashlib.sha256(json.dumps({"archives": rows, "missing": gone}, separators=(",", ":")).encode()).hexdigest()


def read_decision(outdir):
    """→ (rozhodnutí dict | None, důvod). Čte se jednou; brána před i po načtení dat pracuje s tímtéž obsahem (kolo 8)."""
    f = Path(outdir) / SEMANTICS_FILE
    if not f.exists():
        return None, f"chybí {SEMANTICS_FILE} (rozhodnutí o sémantice intervalu fundingu)"
    try:
        d = json.loads(f.read_text())
    except ValueError as e:
        return None, f"{SEMANTICS_FILE} není platný JSON: {e}"
    if not isinstance(d, dict):
        return None, f"{SEMANTICS_FILE}: očekáván objekt"
    return d, "ok"


def check_decision(d):
    """Dodatek 4 + kolo 6/8, bod 5 — kontrola PŘED načtením dat. Samotná existence souboru nestačí."""
    if d.get("semantics") not in ("A", "B"):
        return False, f"{SEMANTICS_FILE}: semantics musí být 'A' nebo 'B'"
    if not d.get("evidence") or not d.get("decided_utc"):
        return False, f"{SEMANTICS_FILE}: chybí evidence nebo decided_utc"
    if d["semantics"] != IMPLEMENTED_SEMANTICS:
        return False, f"rozhodnutá sémantika {d['semantics']} ≠ implementovaná {IMPLEMENTED_SEMANTICS} — nejdřív upravit kód"
    if d.get("performance_hold", True) is not False:
        return False, "performance_hold: výpočet výkonnosti pozastaven vlastníkem (uvolní jen vlastník: performance_hold=false)"
    missing = [k for k in REQUIRED_DECISION_FIELDS if not d.get(k)]
    if missing:
        return False, f"{SEMANTICS_FILE}: chybí {', '.join(missing)} (vazba rozhodnutí na audit, implementaci a data)"
    if d["impl_sha256"] != impl_fingerprint():
        return False, "impl_sha256 neodpovídá běžící implementaci — rozhodnutí platí pro jinou verzi kódu"
    if not (isinstance(d["data_manifest_sha256"], str) and len(d["data_manifest_sha256"]) == 64):
        return False, "data_manifest_sha256 není sha256"
    return True, "ok"


def semantics_gate(outdir):
    d, why = read_decision(outdir)
    return (False, why) if d is None else check_decision(d)


def data_gate(decision, manifest, missing):
    """Kolo 6, bod 5 — kontrola PO načtení a PŘED první simulací: načtená data musí být tatáž, která prošla auditem."""
    got = manifest_fingerprint(manifest, missing)
    if got != decision.get("data_manifest_sha256"):
        return False, f"načtená data ({got[:12]}…) ≠ auditovaný manifest ({str(decision.get('data_manifest_sha256'))[:12]}…)"
    return True, "ok"


# Kolo 6, bod 3: registr datových závad. Každé počítadlo ve flags verdiktu MUSÍ mít třídu; neznámé ⇒ chyba (ne tiché
# přeskočení). blocking > 0 ⇒ kandidát nepostoupí (NEROZHODNUTO); informational verdikt nemění. Metriky výkonnosti
# (Sharpe, PF, počet obchodů…) sem nepatří.
DATA_DEFECTS = {
    "edge_funding_events": "blocking",
    "unfilled_entry_legs": "blocking",
    "legs_with_price_fallback": "blocking",
    "legs_with_funding_gap_in_holding": "blocking",
    "benchmark_funding_missing_events": "blocking",
    "benchmark_funding_discontinuities": "blocking",
    "benchmark_funding_unknown_coverage_assets": "blocking",
    "benchmark_price_fallbacks": "blocking",
    "benchmark_unavailable_at_start": "blocking",
    "duplicate_funding_rows_same_value": "informational",
}


def blocking_defects(flags):
    """{název: počet} nenulových blokujících závad. Neregistrované počítadlo ⇒ KeyError."""
    unknown = [k for k in flags if k not in DATA_DEFECTS]
    if unknown:
        raise KeyError(f"neregistrované počítadlo datové závady: {unknown}")
    return {k: v for k, v in flags.items() if DATA_DEFECTS[k] == "blocking" and v}


BENCHMARK_DEFECT_KEYS = {
    "benchmark_funding_missing_events": lambda r: r["funding_missing_events"],
    "benchmark_funding_discontinuities": lambda r: r["funding_discontinuities"],
    "benchmark_funding_unknown_coverage_assets": lambda r: r["funding_unknown_coverage_assets"],
    "benchmark_price_fallbacks": lambda r: r["price_fallbacks"],
    "benchmark_unavailable_at_start": lambda r: len(r["unavailable_at_start"]),
}
# Kolo 8, bod 1: která kritéria používají benchmark a ze kterého období (viz evaluate). Kritérium, které tu chybí,
# se konzervativně bere jako závislé na benchmarku všech období.
BENCHMARK_DEPENDENCY = {
    "A1_sharpe_dd": ("validation",), "A2_trades_ge_30": (), "A3_x2_pf_profit": (), "A4_wo_top3": (),
    "A5_final_x2": ("final_test",),
    "B1_val_x2_profit_pf": (), "B2_dd_le_0_6_bh": ("validation", "final_test"), "B3_final_x2_profit": (),
    "B4_val_wo_top3": (), "B5_trades_ge_20": (), "B6_tuning_x1_profit": (),
}


def defect_flags(res, bh, market=None):
    """Počty závad pro verdikt: strategie z x1 každého období (scénáře nákladů mají stejná data, nenásobí se),
    benchmark z x1 každého období."""
    f = {"edge_funding_events": sum(res[p]["x1"]["edge_funding_events_excluded"] for p in PERIODS),
         "unfilled_entry_legs": sum(res[p]["x1"]["unfilled_entry_legs"] for p in PERIODS),
         "legs_with_price_fallback": sum(res[p]["x1"]["legs_with_price_fallback"] for p in PERIODS),
         "legs_with_funding_gap_in_holding": sum(res[p]["x1"]["legs_with_funding_gap_in_holding"] for p in PERIODS)}
    f.update({k: sum(get(bh[p]["x1"]) for p in PERIODS) for k, get in BENCHMARK_DEFECT_KEYS.items()})
    if market is not None:
        f["duplicate_funding_rows_same_value"] = sum((market[a].get("load_audit") or {}).get("duplicates_same_value", 0)
                                                     for a in ASSETS)
    return f


def benchmark_defect_periods(bh):
    """{období: {závada: počet}} jen nenulové blokující závady benchmarku (data jsou stejná ve všech scénářích ⇒ x1)."""
    out = {}
    for p in PERIODS:
        d = {k: get(bh[p]["x1"]) for k, get in BENCHMARK_DEFECT_KEYS.items()}
        d = {k: v for k, v in d.items() if v and DATA_DEFECTS[k] == "blocking"}
        if d:
            out[p] = d
    return out


def track_status(track, bad_periods):
    """pass | fail (aspoň jedno porušené kritérium nezávislé na vadném benchmarku) | unknown (všechna porušená kritéria
    závisí na benchmarku s blokující závadou ⇒ zamítnutí nelze prokázat)."""
    failing = [c for c, ok in track.items() if not ok]
    if not failing:
        return "pass", []
    reliable = [c for c in failing if not (set(BENCHMARK_DEPENDENCY.get(c, tuple(PERIODS))) & set(bad_periods))]
    return ("fail", reliable) if reliable else ("unknown", failing)


def final_verdict(track_a, track_b, robust, flags, bench_bad_periods=None):
    """Datová brána na úrovni finálního verdiktu (kolo 6 bod 3, kolo 8 bod 1).
    - robustnost (DSR, sousedé, walk-forward) benchmark nepoužívá ⇒ její selhání = ZAMÍTNUTO bez ohledu na benchmark;
    - prošla-li stopa: blokující závada (strategie nebo benchmarku) ⇒ NEROZHODNUTO, jinak KANDIDÁT;
    - neprošla žádná: je-li některá stopa „unknown“ (zamítnutí stojí jen na kritériích s vadným benchmarkem) ⇒ NEROZHODNUTO,
      jinak ZAMÍTNUTO. Závady strategie zamítnutí nemění (otevřená otázka pro kolo 9).
    Vrací (verdikt, blokující závady, detail)."""
    bad = dict(bench_bad_periods or {})
    blocking = blocking_defects(flags)
    sa, sb = track_status(track_a, bad), track_status(track_b, bad)
    detail = {"track_a": sa[0], "track_b": sb[0], "track_a_reasons": sa[1], "track_b_reasons": sb[1],
              "benchmark_defect_periods": bad, "robust": all(robust.values())}
    if not all(robust.values()):
        return "ZAMÍTNUTO", blocking, detail
    if "pass" in (sa[0], sb[0]):
        if blocking:
            return ("NEROZHODNUTO — datové závady (hrany/mezery fundingu, náhradní ceny, neotevřené nohy, vadný benchmark): "
                    + ", ".join(sorted(blocking))), blocking, detail
        return "KANDIDÁT NA FORWARD PAPER", blocking, detail
    if "unknown" in (sa[0], sb[0]):
        return ("NEROZHODNUTO — zamítnutí stojí jen na kritériích s vadným benchmarkem: "
                + ", ".join(sorted(set(sa[1] if sa[0] == "unknown" else []) | set(sb[1] if sb[0] == "unknown" else [])))
                ), blocking, detail
    return "ZAMÍTNUTO", blocking, detail


LOCK_FILE = ".run.lock"
AUDITS_DIR = "audits"


def latest_audit_dir(outdir):
    d = sorted((Path(outdir) / AUDITS_DIR).glob("*_*"))
    return d[-1] if d else None


def environment_info():
    import platform
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform()}


def atomic_write(path, text):
    """Kolo 8, bod 5: zápis přes dočasný soubor a os.replace ⇒ čtenář vidí starý nebo celý nový obsah, nikdy směs."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


CONFLICT_LOG = "run_conflicts.jsonl"


class RunLock:
    """Kolo 9, Q5: zámek spravovaný OS (fcntl.flock na `.run.lock`). Jádro ho uvolní při jakémkoli ukončení procesu
    (i SIGKILL), soubor se proto nemaže a stáří se nikdy neposuzuje. Souběh ⇒ auditní záznam do run_conflicts.jsonl
    a exit 5 ještě před načtením dat."""
    def __init__(self, outdir):
        self.dir = Path(outdir)
        self.path = self.dir / LOCK_FILE
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, "a+")
        try:
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.fh.seek(0)
            holder = self.fh.read().strip()
            self.fh.close()
            rec = {"utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), "holder": holder,
                   "event": "lock_conflict", "lock": str(self.path)}
            with open(self.dir / CONFLICT_LOG, "a") as log:
                log.write(json.dumps(rec) + "\n")
            print("RUN_REFUSED", json.dumps(rec))
            sys.exit(5)
        self.fh.seek(0)
        self.fh.truncate()
        self.fh.write(json.dumps({"pid": os.getpid(), "since_utc": datetime.now(timezone.utc).isoformat()}))
        self.fh.flush()
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        self.fh.close()
        return False


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_audit_bundle(outdir):
    """Kontrola, že audit_manifest.json popisuje přesně soubory, které leží vedle něj (žádný smíšený manifest)."""
    out = Path(outdir)
    man = json.loads((out / AUDIT_MANIFEST_FILE).read_text())
    bad = [f for f, h in man.get("files_sha256", {}).items() if not (out / f).exists() or file_sha256(out / f) != h]
    return (not bad), bad


def audit_manifest(outdir, produced, data_fp, run_id=None):
    """Kolo 6, bod 5: audit popíše, co sám vytvořil (s sha256 každého souboru, kolo 8); staré výkonnostní soubory
    v adresáři označí jako cizí."""
    out = Path(outdir)
    return {"mode": "audit", "run_id": run_id, "run_utc": datetime.now(timezone.utc).isoformat(),
            "produced_by_this_run": list(produced),
            "files_sha256": {f: file_sha256(out / f) for f in produced if f != AUDIT_MANIFEST_FILE and (out / f).exists()},
            "impl_sha256": impl_fingerprint(), "data_manifest_sha256": data_fp,
            "preexisting_performance_files_not_from_this_run": [f for f in PERFORMANCE_FILES if (out / f).exists()],
            "note": "audit nepočítá výkonnost; případné results.json/trades.csv nejsou výstupem tohoto běhu"}


def data_audit(market):
    """Kontrola dat oddělená od výkonnosti (dodatek 3): všechny přechody funding_interval_hours s okolními časy a počet
    nesouladů rozestupu pro dvě možné sémantiky pole — A: interval platí od dané události k další (předpoklad kódu),
    B: interval popisuje úsek končící danou událostí. Sémantiku rozhodne člověk z konkrétních přechodů, ne kód."""
    out = {}
    for a in ASSETS:
        m = market[a]
        fts = m["fts"]
        trans, mis_a, mis_b, mis_bt = [], 0, 0, 0
        for k in range(len(fts) - 1):
            sp = (fts[k + 1] - fts[k]) / HOUR_MS
            ia, ib = m["finterval"][fts[k]], m["finterval"][fts[k + 1]]
            mis_a += sp != ia
            mis_b += sp != ib
            mis_bt += not spacing_ok(fts[k], ia, fts[k + 1], ib)
            if ia != ib:
                ctx = [(datetime.fromtimestamp(fts[j] / 1000, tz=timezone.utc).isoformat(), m["finterval"][fts[j]])
                       for j in range(max(0, k - 2), min(len(fts), k + 4))]
                trans.append({"at": datetime.fromtimestamp(fts[k + 1] / 1000, tz=timezone.utc).isoformat(),
                              "from_h": ia, "to_h": ib, "spacing_h": sp, "context": ctx})
        out[a] = {"funding_events": len(fts), "interval_transitions": trans,
                  "spacing_mismatch_semantics_A": mis_a, "spacing_mismatch_semantics_B": mis_b,
                  "spacing_mismatch_semantics_B_tolerant_implemented": mis_bt,
                  "hour_bars": len(m["bts"]),
                  "missing_hour_ranges": [{"from": datetime.fromtimestamp((a_ + HOUR_MS) / 1000, tz=timezone.utc).isoformat(),
                                           "hours": (b_ - a_) // HOUR_MS - 1}
                                          for a_, b_ in zip(m["bts"], m["bts"][1:]) if b_ - a_ > HOUR_MS],
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


REQUEST_MODES = {"AUDIT": "audit", "PERF": "perf"}


def mode_from_request(path):
    """Whitelist režimů (kolo 6, bod 5): první slovo RUN_REQUEST musí být AUDIT nebo PERF. Neznámé/prázdné ⇒ exit 4.
    Dřív platilo „cokoli nezačínající AUDIT = výkon“."""
    try:
        words = Path(path).read_text().split()
    except OSError as e:
        print("MODE_REFUSED", f"RUN_REQUEST nelze číst: {e}")
        sys.exit(4)
    if not words or words[0] not in REQUEST_MODES:
        print("MODE_REFUSED", f"neznámý režim {words[0] if words else '(prázdný)'!r}; povoleno {sorted(REQUEST_MODES)}")
        sys.exit(4)
    return REQUEST_MODES[words[0]]


def robustness_checks(dsr, nb, wf):
    wf_pos = sum(1 for y in wf.values() if y["net_pnl"] > 0)
    return {"dsr_ge_0_95": dsr["dsr"] is not None and dsr["dsr"] >= 0.95,
            "neighbors_val_x2_profit": all(v > 0 for v in nb.values()),
            "walk_forward_ge_3_of_4": wf_pos >= 3}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-fd")
    ap.add_argument("--outdir", default="research/funding_dispersion")
    ap.add_argument("--audit-only", action="store_true", help="= --mode audit (zpětná kompatibilita)")
    ap.add_argument("--mode", choices=("audit", "perf"), help="audit = jen kontrola dat; perf = výkonnost (za branou)")
    ap.add_argument("--request-file", help="RUN_REQUEST: první slovo AUDIT ⇒ audit, PERF ⇒ výkon, jinak odmítnutí")
    ap.add_argument("--print-fingerprints", action="store_true", help="vypsat otisk implementace a skončit")
    args = ap.parse_args(argv)
    if args.print_fingerprints:
        print("IMPL_SHA256", impl_fingerprint())
        return
    modes = {m for m in ("audit" if args.audit_only else None, args.mode,
                         mode_from_request(args.request_file) if args.request_file else None) if m}
    if len(modes) > 1:
        print("MODE_REFUSED rozporné zadání režimu", sorted(modes))
        sys.exit(4)
    mode = modes.pop() if modes else None
    if mode is None:  # kolo 6, bod 5: režim musí být explicitní, žádné „vše ostatní = výkon“
        print("MODE_REFUSED zadej --mode audit nebo --mode perf")
        sys.exit(4)
    out = Path(args.outdir)
    with RunLock(out):  # kolo 8, bod 5: souběžný běh nad stejným adresářem ⇒ exit 5
        return _execute(mode, args, out)


def _execute(mode, args, out):
    run_id = uuid.uuid4().hex
    decision = None
    if mode == "perf":
        decision, why = read_decision(out)  # čte se jednou, obě brány používají tentýž obsah
        ok, why = (False, why) if decision is None else check_decision(decision)
        if not ok:  # kontrola PŘED stažením dat a před jakýmkoli výpočtem
            print("PERFORMANCE_REFUSED", why)
            sys.exit(3)
    market, manifest, missing, fatal = load(args.cache)
    data_fp = manifest_fingerprint(manifest, missing)
    if mode == "perf":
        ok, why = data_gate(decision, manifest, missing)
        if not ok:  # data se načetla, ale simulace nesmí proběhnout; nic se nezapisuje
            print("PERFORMANCE_REFUSED", why)
            sys.exit(3)
    # Kolo 9, Q4: audit zapisuje do vlastního podadresáře audits/<UTC>_<run_id>/ ⇒ nikdy nepřepíše dřívější audit ani
    # výsledky výkonnosti v outdir; výkonnostní běh zapisuje jako dosud do outdir.
    dest = out
    if mode == "audit":
        dest = out / AUDITS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{run_id[:12]}"
        dest.mkdir(parents=True, exist_ok=False)
    atomic_write(dest / "data_source.json", json.dumps({"run_id": run_id, "archives": manifest, "missing": missing,
                                                        "data_manifest_sha256": data_fp}, indent=1))
    if fatal:
        print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
        sys.exit(2)
    audit = data_audit(market)
    atomic_write(dest / "data_audit.json", json.dumps(audit, indent=1, default=str))
    print("DATA_AUDIT", json.dumps({a: {k: v for k, v in x.items() if k != "interval_transitions"} | {
        "interval_transitions": len(x["interval_transitions"])} for a, x in audit.items()}, default=str))
    if mode == "audit":
        man = audit_manifest(dest, ("data_source.json", "data_audit.json", AUDIT_MANIFEST_FILE), data_fp, run_id)
        man["outdir_performance_files_not_from_this_run"] = [f for f in PERFORMANCE_FILES if (out / f).exists()]
        man["environment"] = environment_info()
        atomic_write(dest / AUDIT_MANIFEST_FILE, json.dumps(man, indent=1))  # zapisuje se poslední, s hashi souborů
        print("AUDIT_MANIFEST", json.dumps(man))
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
    robust = robustness_checks(dsr, nb, wf)
    s, e = PERIODS["validation"]
    beta_info = {"corr_daily_vs_btc_validation_x1": corr(rets_store[(ctag, "validation", 1)],
                                                         btc_daily_returns(market, pdate(s), pdate(e), px)),
                 "gross_exposure_strategy": 4 * LEG_FRACTION, "gross_exposure_bh": 1.0,
                 "bh_vol_matched_x1": {p: vol_matched(rets_store[(ctag, p, 1)], bh_rets[(p, 1)])
                                       for p in ("validation", "final_test")}}
    flags = defect_flags(res, bh, market)
    verdict, blocking, verdict_detail = final_verdict(track_a, track_b, robust, flags, benchmark_defect_periods(bh))
    payload = {"protocol": "research/funding_dispersion/PROTOCOL.md", "chosen": ctag,
               "tuning_selection_x1": tune, "strategy": results, "buy_hold_equal_8": bh,
               "walk_forward_x2": wf,
               "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-10…2022; pro 2021–22 NE čistý OOS walk-forward", "neighbors_val_x2": nb, "track_a": track_a, "track_b": track_b,
               "passed_a": passed_a, "passed_b": passed_b, "dsr_validation_x1": dsr,
               "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
               "dsr_sensitivity_scenarios": dsr_sens, "robustness": robust, "interpretation_flags": flags,
               "blocking_data_defects": blocking, "data_defect_classes": DATA_DEFECTS,
               "verdict_detail": verdict_detail, "benchmark_dependency": BENCHMARK_DEPENDENCY, "run_id": run_id,
               "impl_sha256": impl_fingerprint(), "data_manifest_sha256": data_fp,
               "unfilled_entries_x1": {p: res[p]["x1"]["unfilled_entries"] for p in PERIODS},
               "info": {**beta_info, "price_fallbacks_by_purpose": px.fallbacks, "first_bar": first_bar,
                        "first_funding": first_funding,
                        "load_audit": {a: market[a].get("load_audit") for a in ASSETS}},
               "verdict": verdict}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else ["period"])
    w.writeheader()
    w.writerows(rows)
    atomic_write(out / "trades.csv", buf.getvalue())
    payload["trades_csv_sha256"] = file_sha256(out / "trades.csv")  # results.json se zapisuje poslední a váže trades.csv
    atomic_write(out / "results.json", json.dumps(payload, indent=1, default=str))
    print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
                                 "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "flags": flags,
                                 "neighbors": nb,
                                 "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
                                 "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
                                 "wf": {k: v["net_pnl"] for k, v in wf.items()}, **beta_info,
                                 "fallbacks": px.fallbacks}, default=str))


if __name__ == "__main__":
    main()
