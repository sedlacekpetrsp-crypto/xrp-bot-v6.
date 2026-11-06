"""Spot-led price discovery spot → USDT-M perp, 5m, BTC/ETH/XRP (H-20261106-3) — backtest podle PROTOCOL.md.
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.spot_led.run --cache /tmp/vision-5m --outdir research/spot_led
"""
import argparse
import ast
import bisect
import csv
import hashlib
import heapq
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

ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT")
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2026, 10)
FEE, SLIP = 0.00095, 0.0002
COST_MULTIPLIERS = (1, 2, 3)
GRID = [(th, hold) for th in (0.65, 0.70) for hold in (15, 30)]  # (p_hi; p_lo = 1 − p_hi, držení min)
R_SPOT, R_PERP = 0.002, 0.001
PERIODS = {"tuning": ("2020-02-01", "2022-12-31"),
           "validation": ("2023-01-01", "2024-12-31"),
           "final_test": ("2025-01-01", "2026-10-31")}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
FRACTION = 0.10
DSR_N, DSR_VAR_ANNUAL = 159, 0.5
BAR = 300_000
HOUR_MS = 3_600_000
DAY_MS = 86_400_000


def vt(th, hold):
    return f"P{int(round(th * 100))}_H{hold}"


# ------------------------------------------------------------------ data
def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _csv_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


def parse_spot(payload):
    """→ [(ts, close, volume, taker_buy_base)]"""
    return [(_ms(int(r[0])), float(r[4]), float(r[5]), float(r[9])) for r in _csv_rows(payload)]


def parse_perp(payload):
    """→ [(ts, open, close)]"""
    return [(_ms(int(r[0])), float(r[1]), float(r[4])) for r in _csv_rows(payload)]


def normalize_funding_ts(ts):
    near = round(ts / HOUR_MS) * HOUR_MS
    if abs(ts - near) > 1000:
        raise ValueError(f"funding timestamp {ts} je {ts - near} ms od celé hodiny")
    return near


def parse_funding(payload):
    """→ [(normalizovaný čas, sazba, funding_interval_hours)] (dodatek 2: interval kvůli kontrole úplnosti)."""
    return [(normalize_funding_ts(_ms(int(r[0]))), float(r[2]), float(r[1])) for r in _csv_rows(payload)]


def urls(asset):
    b = "https://data.binance.vision/data"
    for y, m in months():
        tag = f"{y}-{m:02d}"
        yield "spot", (y, m), f"{b}/spot/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
        yield "perp", (y, m), f"{b}/futures/um/monthly/klines/{asset}/5m/{asset}-5m-{tag}.zip"
        yield "fr", (y, m), f"{b}/futures/um/monthly/fundingRate/{asset}/{asset}-fundingRate-{tag}.zip"


def load(cache, fetcher=fetch):
    market, manifest, missing, fatal = {}, [], [], []
    parsers = {"spot": parse_spot, "perp": parse_perp, "fr": parse_funding}
    for a in ASSETS:
        raw = {"spot": {}, "perp": {}, "fr": {}}
        load_audit = {"duplicates_same_value": 0}
        present, miss = {k: [] for k in raw}, {k: [] for k in raw}
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
            rows = parsers[kind](payload)
            for r in rows:
                add_row(raw[kind], r[0], r[1:] if kind != "fr" else (r[1], r[2]), a, kind, load_audit)
            manifest.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)})
        for kind in raw:
            if present[kind]:
                first = min(present[kind])
                fatal += [{"asset": a, "kind": kind, "month": f"{y}-{m:02d}"} for (y, m) in miss[kind] if (y, m) > first]
            else:
                fatal.append({"asset": a, "kind": kind, "month": "all"})
        market[a] = prepare(raw["spot"], raw["perp"], raw["fr"])
        market[a]["load_audit"] = load_audit
    return market, manifest, missing, fatal


def add_row(store, ts, value, asset, kind, audit):
    """Kolo 8 (nález R8-2): duplicitní čas se stejnou hodnotou = počítat; s jinou hodnotou = chyba. Dřív se tiše
    přepsal pozdějším řádkem (u fundingu i svíček)."""
    if ts in store:
        if store[ts] != value:
            raise ValueError(f"konfliktní duplicita {kind} {asset} {ts}: {store[ts]} vs {value}")
        audit["duplicates_same_value"] += 1
        return
    store[ts] = value


def prepare(spot, perp, fund):
    """spot {ts: (close, vol, taker_buy)}, perp {ts: (open, close)}, fund {ts: rate | (rate, interval_h)}.
    Holá sazba (syntetické testy) = interval 8 h."""
    perp_ts = sorted(perp)
    f = {ts: (v if isinstance(v, tuple) else (v, 8.0)) for ts, v in sorted(fund.items())}
    return {"spot": spot, "perp": perp, "perp_ts": perp_ts, "funding": {ts: v[0] for ts, v in f.items()},
            "finterval": {ts: v[1] for ts, v in f.items()}, "fts": list(f), "features": features(spot, perp)}


def features(spot, perp):
    """Pro každý spot čas T se svíčkami T a T−5m v obou trzích: (T, podíl, r_spot, r_perp). Jen data ≤ T."""
    out = []
    for T in sorted(spot):
        s, sp = spot[T], spot.get(T - BAR)
        p, pp = perp.get(T), perp.get(T - BAR)
        if sp is None or p is None or pp is None or s[1] <= 0 or sp[0] <= 0 or pp[1] <= 0:
            continue
        out.append((T, s[2] / s[1], s[0] / sp[0] - 1, p[1] / pp[1] - 1))
    return out


def gap_audit(m):
    spot, perp = m["spot"], m["perp"]
    def missing(ts_sorted):
        return sum(max(0, (b - a) // BAR - 1) for a, b in zip(ts_sorted, ts_sorted[1:]))
    ss = set(spot)
    ps = set(perp)
    return {"spot_bars": len(spot), "perp_bars": len(perp), "spot_missing_5m": missing(sorted(spot)),
            "perp_missing_5m": missing(m["perp_ts"]), "spot_only": len(ss - ps), "perp_only": len(ps - ss),
            "usable_signal_bars": len(m["features"])}


# ------------------------------------------------------------------ simulace
def ms_of(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def date_of(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


MAX_PRICE_AGE_MS = 60 * 60_000  # dodatek 2: náhradní cena starší než 60 min ⇒ obchod/den nehodnotitelný


def perp_price_at(m, t):
    """(cena, stáří ms, náhrada?): open svíčky v t (stáří 0, bez náhrady); chybí-li, close poslední svíčky UZAVŘENÉ
    do t (stáří = t − čas uzavření, náhrada = True). Žádná dřívější svíčka ⇒ None — nikdy budoucí cena (dodatek 2)."""
    b = m["perp"].get(t)
    if b is not None:
        return b[0], 0, False
    i = bisect.bisect_right(m["perp_ts"], t - BAR) - 1
    if i < 0:
        return None
    ts = m["perp_ts"][i]
    return m["perp"][ts][1], t - (ts + BAR), True


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
        return None
    gaps, k = 0, i
    while k + 1 < len(fts) and fts[k + 1] <= hi:
        if not spacing_ok(fts[k], m["finterval"][fts[k]], fts[k + 1], m["finterval"][fts[k + 1]]):
            gaps += 1
        k += 1
    if fts[k] + m["finterval"][fts[k]] * HOUR_MS <= hi:
        gaps += 1  # očekávaná událost ≤ hi chybí
    return gaps


def funding_window(m, entry, exit_):
    """Jediná konvence hranic držení pro účtování i kontrolu úplnosti (kolo 6, bod 2): události s entry < t < exit
    (strategie: komentář a smyčka v candidates; nově i benchmark). Vrací seřazené časy událostí v řadě."""
    fts = m["fts"]
    return fts[bisect.bisect_right(fts, entry):bisect.bisect_left(fts, exit_)]


def funding_completeness(m, entry, exit_):
    """Úplnost fundingu pro držení (entry, exit) se stejnými hranicemi jako funding_window (kolo 6, body 1 a 2):
    nesouvislosti (= funding_chain_gaps na (entry, exit − 1]), odhad chybějících událostí a neznámé pokrytí."""
    if exit_ <= entry:  # kolo 8: prázdné držení nemá co pokrýt
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
            step = iv[fts[k + 1]] * HOUR_MS
            missing += max(1, -(-(fts[k + 1] - fts[k]) // step) - 1)
        k += 1
    step = iv[fts[k]] * HOUR_MS
    if fts[k] + step <= hi:
        missing += (hi - fts[k]) // step
    return {"discontinuities": disc, "missing_events": int(missing), "unknown_coverage": False}


MAX_EXIT_DELAY_MS = 60 * 60_000  # dodatek 1: výstup se smí kvůli mezeře zpozdit nejvýš o 60 min


def candidates(m, asset, start_ms, end_ms, th, hold, delay_bars=0, include_unfilled=False):
    """Kandidátní obchody jednoho aktiva (nezávislé na equity): bez překryvu, výstup uvnitř období.
    delay_bars: informativní citlivost na latenci (vstup o N svíček později), výběr varianty neovlivňuje.
    Okraj období se posuzuje jen podle času (plánovaný výstup + max. zpoždění < konec), ne podle existence dat.
    include_unfilled (kolo 6, bod 4): signál bez vstupní svíčky se vrátí jako záznam {"unfilled": True, …} bez ceny,
    notionalu a cooldownu (blokace aktiva free_from se nemění); notional dopočte portfolio simulátor."""
    hold_ms = hold * 60_000
    out, free_from = [], -1
    feats = m["features"]
    i = bisect.bisect_left(feats, (start_ms - BAR,))  # vstup (T+5m) ≥ start
    for T, share, rs, rp in feats[i:]:
        entry_t = T + BAR * (1 + delay_bars)
        if entry_t >= end_ms:
            break
        if entry_t < start_ms or T + BAR < free_from:
            continue
        if share > th and rs > R_SPOT and rp < R_PERP:
            side = 1
        elif share < 1 - th and rs < -R_SPOT and rp > -R_PERP:
            side = -1
        else:
            continue
        planned = entry_t + hold_ms
        if planned + MAX_EXIT_DELAY_MS >= end_ms:
            continue
        if entry_t not in m["perp"]:
            if include_unfilled:
                out.append({"unfilled": True, "asset": asset, "side": side, "signal_ts": T, "entry_ts": entry_t,
                            "reason": "missing_entry_candle"})
            continue
        j = bisect.bisect_left(m["perp_ts"], planned)
        if j < len(m["perp_ts"]) and m["perp_ts"][j] <= planned + MAX_EXIT_DELAY_MS:
            exit_t = m["perp_ts"][j]
            exit_px = m["perp"][exit_t][0]
            gap = int(exit_t != planned)
        else:  # mezera delší než limit ⇒ DATA_GAP: poslední pozorovaný close před plánovaným výstupem (nerealizovatelné)
            k = bisect.bisect_left(m["perp_ts"], planned) - 1
            exit_t = planned + MAX_EXIT_DELAY_MS
            exit_px = m["perp"][m["perp_ts"][k]][1]
            gap = 2
        # funding: události s entry_t < t < exit_t (seznam pro denní ocenění přes půlnoc)
        f_events, f_fallbacks, f_max_age, unevaluable = [], 0, 0, 0
        for t in funding_window(m, entry_t, exit_t):
            pa = perp_price_at(m, t)
            if pa is None or pa[1] > MAX_PRICE_AGE_MS:
                unevaluable = 1
            if pa is not None:
                f_fallbacks += pa[2]
                f_max_age = max(f_max_age, pa[1])
                f_events.append((t, -side * m["funding"][t] * pa[0]))
        fc = funding_completeness(m, entry_t, exit_t)
        fg = None if fc["unknown_coverage"] else fc["discontinuities"]
        out.append({"asset": asset, "side": side, "signal_ts": T, "entry_ts": entry_t, "exit_ts": exit_t,
                    "entry": m["perp"][entry_t][0], "exit": exit_px, "funding_unit": sum(x for _, x in f_events),
                    "funding_events": f_events, "share": share, "r_spot": rs, "r_perp": rp, "data_gap": gap,
                    "funding_price_fallbacks": f_fallbacks, "funding_price_max_age_min": f_max_age / 60_000,
                    "funding_gaps": 1 if fg is None else fg, "unevaluable": unevaluable})
        free_from = exit_t
    return out


def close_before(m, t):
    """(close, stáří ms) poslední perp svíčky uzavřené nejpozději v t; žádná ⇒ None (nikdy budoucí cena)."""
    i = bisect.bisect_right(m["perp_ts"], t - BAR) - 1
    if i < 0:
        return None
    ts = m["perp_ts"][i]
    return m["perp"][ts][1], t - (ts + BAR)


def simulate(market, start, end, th, hold, mult, variant="", delay_bars=0):
    """(obchody, denní equity) — viz simulate_full."""
    return simulate_full(market, start, end, th, hold, mult, variant, delay_bars)[:2]


def simulate_full(market, start, end, th, hold, mult, variant="", delay_bars=0):
    """Sdílená equity: notional = 10 % realizované equity při vstupu. Vrací (obchody, denní equity).
    Denní equity = realizované obchody + ocenění pozic otevřených přes půlnoc (close poslední svíčky dne,
    vstupní náklady, funding do půlnoci) — oprava podle oponentury (bod G). Vrací (obchody, equity, nevyplněné vstupy)."""
    c = (FEE + SLIP) * mult
    s_ms, e_ms = ms_of(start), ms_of(end) + DAY_MS
    cands = sorted((x for a in ASSETS for x in candidates(market[a], a, s_ms, e_ms, th, hold, delay_bars,
                                                          include_unfilled=True)),
                   key=lambda x: (x["entry_ts"], x["asset"]))
    cash, pending, trades, unfilled = START_EQUITY, [], [], []
    for x in cands:
        while pending and pending[0][0] <= x["entry_ts"]:
            _, _, tr = heapq.heappop(pending)
            cash += tr["net_pnl"]
        if x.get("unfilled"):  # kolo 6, bod 4: jen evidence, žádná pozice, poplatek ani změna equity
            unfilled.append({**x, "variant": variant, "planned_notional": FRACTION * cash})
            continue
        notional = FRACTION * cash
        qty = notional / x["entry"]
        gross = x["side"] * qty * (x["exit"] - x["entry"])
        costs = notional * c + qty * x["exit"] * c
        fund = qty * x["funding_unit"]
        tr = {**x, "variant": variant, "cost_mult": mult, "qty": qty, "notional": notional, "gross": gross,
              "funding": fund, "costs": costs, "net_pnl": gross + fund - costs, "cost_in": notional * c,
              "gross_bp": x["side"] * (x["exit"] / x["entry"] - 1) * 1e4}
        trades.append(tr)
        heapq.heappush(pending, (x["exit_ts"], len(trades), tr))
    # Jednotná konvence dne (dodatek 2, stejná pro benchmark): den d = [d 00:00, d+1 00:00); ocenění na konci dne
    # proběhne PŘED událostmi v přesně 00:00 (funding, výstup, vstup v 00:00 patří novému dni). Pozice otevřená v
    # okamžiku konce dne (vstup < konec ≤ výstup) se ocení close poslední uzavřené svíčky dne.
    realized_by_day, overnight = {}, {}
    for tr in trades:
        d = date_of(tr["exit_ts"])
        realized_by_day[d] = realized_by_day.get(d, 0.0) + tr["net_pnl"]
        tr["stale_mtm"] = 0
        day_end = (tr["entry_ts"] // DAY_MS + 1) * DAY_MS
        while day_end <= tr["exit_ts"]:
            p, age = close_before(market[tr["asset"]], day_end)
            tr["stale_mtm"] += age > MAX_PRICE_AGE_MS
            mtm = tr["side"] * tr["qty"] * (p - tr["entry"]) - tr["cost_in"] + \
                tr["qty"] * sum(v for t, v in tr["funding_events"] if t < day_end)
            dd = date_of(day_end - 1)
            overnight[dd] = overnight.get(dd, 0.0) + mtm
            day_end += DAY_MS
    curve, eq, d = {}, START_EQUITY, start
    while d <= end:
        eq += realized_by_day.get(d, 0.0)
        curve[d] = eq + overnight.get(d, 0.0)
        d += timedelta(days=1)
    return trades, curve, unfilled


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


def trade_metrics(trades, start, end):
    pnl = [t["net_pnl"] for t in trades]
    gains = sum(p for p in pnl if p > 0)
    losses = -sum(p for p in pnl if p < 0)
    top3 = sum(sorted(pnl, reverse=True)[:3])
    years = max((end - start).days + 1, 1) / 365.25
    return {"trades": len(pnl), "net_pnl": round(sum(pnl), 4),
            "profit_factor": round(gains / losses, 4) if losses > 0 else (None if gains == 0 else 999.0),
            "net_without_top3": round(sum(pnl) - top3, 4),
            "funding": round(sum(t["funding"] for t in trades), 4),
            "costs": round(sum(t["costs"] for t in trades), 4),
            "long_trades": sum(1 for t in trades if t["side"] == 1),
            "short_trades": sum(1 for t in trades if t["side"] == -1),
            "data_gap_exits": sum(1 for t in trades if t["data_gap"]),
            "data_gap_unrealizable_exits": sum(1 for t in trades if t["data_gap"] == 2),
            "funding_price_fallback_trades": sum(1 for t in trades if t["funding_price_fallbacks"]),
            "funding_price_max_age_min": max([t["funding_price_max_age_min"] for t in trades], default=0),
            "funding_gap_trades": sum(1 for t in trades if t["funding_gaps"]),
            "unevaluable_trades": sum(t["unevaluable"] for t in trades),
            "stale_mtm_trades": sum(1 for t in trades if t.get("stale_mtm")),
            "avg_gross_bp": round(sum(t["gross_bp"] for t in trades) / len(trades), 3) if trades else None,
            "trades_per_year_per_asset": {a: round(sum(1 for t in trades if t["asset"] == a) / years, 1)
                                          for a in ASSETS}}


def run(market, start, end, mult, th, hold, variant, delay_bars=0):
    trades, curve, unfilled = simulate_full(market, start, end, th, hold, mult, variant, delay_bars)
    cm, rets = curve_metrics(curve, START_EQUITY)
    return {**cm, **trade_metrics(trades, start, end), "unfilled_entries": len(unfilled),
            "unfilled_entry_records": [{"asset": u["asset"], "side": u["side"], "signal_utc": iso(u["signal_ts"]),
                                        "entry_utc": iso(u["entry_ts"]), "planned_notional": round(u["planned_notional"], 6),
                                        "reason": u["reason"]} for u in unfilled]}, trades, rets


def day_close(m, d):
    """(close, stáří ms) poslední svíčky uzavřené do konce dne d; prázdný prefix ⇒ None (oprava: dřív index −1 = budoucí cena)."""
    return close_before(m, ms_of(d) + DAY_MS)


def buy_hold(market, start, end, mult):
    """B&H 3 perpů stejnými vahami, 1× bez páky, včetně skutečného fundingu (long platí kladnou sazbu).
    Konvence dne jako u strategie: událost v přesně 00:00 patří novému dni. Nákup za open první svíčky v [start, start + 60 min];
    aktivum bez svíčky v tomto okně = hotovost po celé období (`unavailable_at_start`), nikdy pozdější/budoucí cena.
    Kolo 6, body 1–3: každé aktivum má vlastní skutečný čas nákupu entry_ts[a]; funding se účtuje podle funding_window
    (entry_ts[a] < t < prodej, stejně jako strategie) a úplnost řady podle funding_completeness. Prodej = close poslední
    svíčky dne `end`, tj. v čase konce dne. Náhradní/zastaralé ceny a mezery se vrací jako počty pro registr DATA_DEFECTS."""
    c = (FEE + SLIP) * mult
    t0 = ms_of(start)
    t_end = ms_of(end) + DAY_MS
    share = START_EQUITY / len(ASSETS)
    qty, entry_ts, cash, unavailable = {}, {}, 0.0, []
    for a in ASSETS:
        m = market[a]
        j = bisect.bisect_left(m["perp_ts"], t0)
        if j < len(m["perp_ts"]) and m["perp_ts"][j] <= t0 + MAX_PRICE_AGE_MS:
            entry_ts[a] = m["perp_ts"][j]
            qty[a] = share * (1 - c) / m["perp"][entry_ts[a]][0]
        else:
            cash += share
            unavailable.append(a)
    completeness = {a: funding_completeness(market[a], entry_ts[a], t_end) for a in qty}
    events = sorted((t, a) for a in qty for t in funding_window(market[a], entry_ts[a], t_end))
    k, funding, curve, d, stale, fb = 0, 0.0, {}, start, 0, 0
    while d <= end:
        t_day = ms_of(d) + DAY_MS
        while k < len(events) and events[k][0] < t_day:
            te, a = events[k]
            pa = perp_price_at(market[a], te)  # entry_ts[a] < te ⇒ existuje dřívější svíčka, nikdy None
            fb += pa[2]
            stale += pa[1] > MAX_PRICE_AGE_MS
            funding -= market[a]["funding"][te] * qty[a] * pa[0]
            k += 1
        val = 0.0
        for a, q in qty.items():
            p, age = day_close(market[a], d)
            stale += age > MAX_PRICE_AGE_MS
            val += q * p
        curve[d] = cash + funding + val
        d += timedelta(days=1)
    curve[end] = cash + funding + (curve[end] - cash - funding) * (1 - c)
    cm, _ = curve_metrics(curve, START_EQUITY)
    return {**cm, "net_pnl": round(curve[end] - START_EQUITY, 4), "funding": round(funding, 4),
            "entry_utc": {a: iso(t) for a, t in entry_ts.items()},
            "unavailable_at_start": unavailable, "stale_valuations": stale, "funding_price_fallbacks": fb,
            "funding_completeness": completeness,
            "funding_missing_events": sum(x["missing_events"] for x in completeness.values()),
            "funding_discontinuities": sum(x["discontinuities"] for x in completeness.values()),
            "funding_unknown_coverage_assets": sum(x["unknown_coverage"] for x in completeness.values())}


def safe_dsr(rets, n, var_annual):
    """Nedefinované DSR (nulový rozptyl, např. 0 obchodů) = None + důvod; brána pak neprošla."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.research.deflated_sharpe import dsr_from_returns
    try:
        return {**dsr_from_returns(rets, n, var_annual / 365), "undefined_reason": None}
    except (ValueError, ZeroDivisionError) as e:
        return {"dsr": None, "undefined_reason": str(e), "n_trials": n, "var_trials": var_annual / 365}


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


def neighbors(th, hold):
    return [(t2, h2) for (t2, h2) in GRID if (t2 == th) != (h2 == hold)]


def pdate(s):
    return date.fromisoformat(s)


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def trade_row(period, t):
    return {"period": period, "variant": t["variant"], "cost_mult": t["cost_mult"], "asset": t["asset"],
            "side": "LONG" if t["side"] == 1 else "SHORT", "signal_bar_utc": iso(t["signal_ts"]),
            "entry_utc": iso(t["entry_ts"]), "exit_utc": iso(t["exit_ts"]), "entry": t["entry"], "exit": t["exit"],
            "taker_buy_share": round(t["share"], 6), "r_spot": round(t["r_spot"], 6), "r_perp": round(t["r_perp"], 6),
            "qty": round(t["qty"], 10), "notional": round(t["notional"], 6), "gross": round(t["gross"], 6),
            "funding": round(t["funding"], 6), "costs": round(t["costs"], 6), "data_gap": t["data_gap"],
            "funding_price_fallbacks": t["funding_price_fallbacks"], "funding_gaps": t["funding_gaps"],
            "unevaluable": t["unevaluable"], "stale_mtm": t.get("stale_mtm", 0),
            "net_pnl": round(t["net_pnl"], 6)}


IMPLEMENTED_SEMANTICS = "B"  # spacing_ok: interval záznamu = úsek končící událostí, tolerance při změně nastavení
SEMANTICS_FILE = "FUNDING_SEMANTICS.json"
AUDIT_MANIFEST_FILE = "audit_manifest.json"
PERFORMANCE_FILES = ("results.json", "trades.csv", "trades.csv.gz")
# Kolo 8, bod 2: otisk celé implementace (tento soubor + modul DSR) z AST bez docstringů a komentářů + Python major.minor.
FINGERPRINT_SOURCES = ("research/spot_led/run.py", "tools/research/deflated_sharpe.py")
REQUIRED_DECISION_FIELDS = ("semantics", "evidence", "decided_utc", "audit_id", "impl_sha256", "data_manifest_sha256")


def _strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body \
                and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    return tree


def code_fingerprint(sources):
    h = hashlib.sha256(f"python{sys.version_info[0]}.{sys.version_info[1]}".encode())
    for name in sorted(sources):
        tree = _strip_docstrings(ast.parse(sources[name]))
        h.update(name.encode() + b"\0" + ast.dump(tree, include_attributes=False).encode() + b"\0")
    return h.hexdigest()


def impl_fingerprint():
    root = Path(__file__).resolve().parents[2]
    return code_fingerprint({rel: (root / rel).read_text() for rel in FINGERPRINT_SOURCES})


def manifest_fingerprint(manifest, missing=()):
    """sha256 skutečně načtených dat: seřazené (url, sha256 archivu) + seřazené chybějící url."""
    rows = sorted((x["url"], x["sha256"]) for x in manifest)
    gone = sorted(x["url"] for x in missing)
    return hashlib.sha256(json.dumps({"archives": rows, "missing": gone}, separators=(",", ":")).encode()).hexdigest()


def read_decision(outdir):
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
    got = manifest_fingerprint(manifest, missing)
    if got != decision.get("data_manifest_sha256"):
        return False, f"načtená data ({got[:12]}…) ≠ auditovaný manifest ({str(decision.get('data_manifest_sha256'))[:12]}…)"
    return True, "ok"


# Kolo 6, bod 3: registr datových závad; neregistrované počítadlo ⇒ chyba, blocking > 0 ⇒ kandidát nepostoupí.
DATA_DEFECTS = {
    "data_gap_unrealizable_exits": "blocking",
    "funding_price_fallback_trades": "blocking",
    "funding_gap_trades": "blocking",
    "unevaluable_trades": "blocking",
    "stale_mtm_trades": "blocking",
    "unfilled_entries": "blocking",
    "benchmark_stale_valuations": "blocking",
    "benchmark_unavailable_at_start": "blocking",
    "benchmark_funding_price_fallbacks": "blocking",
    "benchmark_funding_missing_events": "blocking",
    "benchmark_funding_discontinuities": "blocking",
    "benchmark_funding_unknown_coverage_assets": "blocking",
    "data_gap_exits_within_limit": "informational",  # výstup zpožděný ≤ 60 min podle dodatku 1
    "duplicate_rows_same_value": "informational",
}
BENCHMARK_DEFECT_KEYS = {
    "benchmark_stale_valuations": lambda r: r["stale_valuations"],
    "benchmark_unavailable_at_start": lambda r: len(r["unavailable_at_start"]),
    "benchmark_funding_price_fallbacks": lambda r: r["funding_price_fallbacks"],
    "benchmark_funding_missing_events": lambda r: r["funding_missing_events"],
    "benchmark_funding_discontinuities": lambda r: r["funding_discontinuities"],
    "benchmark_funding_unknown_coverage_assets": lambda r: r["funding_unknown_coverage_assets"],
}
# Kolo 8, bod 1: kritéria používající benchmark a období (viz evaluate); chybějící kritérium = závislé na všech obdobích.
BENCHMARK_DEPENDENCY = {
    "A1_sharpe_dd": ("validation",), "A2_trades_ge_30": (), "A3_x2_pf_profit": (), "A4_wo_top3": (),
    "A5_final_x2": ("final_test",),
    "B1_val_x2_profit_pf": (), "B2_dd_le_0_6_bh": ("validation", "final_test"), "B3_final_x2_profit": (),
    "B4_val_wo_top3": (), "B5_trades_ge_20": (), "B6_tuning_x1_profit": (),
}


def blocking_defects(flags):
    unknown = [k for k in flags if k not in DATA_DEFECTS]
    if unknown:
        raise KeyError(f"neregistrované počítadlo datové závady: {unknown}")
    return {k: v for k, v in flags.items() if DATA_DEFECTS[k] == "blocking" and v}


def defect_flags(res, bh, market=None):
    """Strategie i benchmark z x1 každého období (nákladové scénáře mají stejná data, nenásobí se)."""
    st = lambda k: sum(res[p]["x1"][k] for p in PERIODS)
    f = {"data_gap_unrealizable_exits": st("data_gap_unrealizable_exits"),
         "funding_price_fallback_trades": st("funding_price_fallback_trades"),
         "funding_gap_trades": st("funding_gap_trades"), "unevaluable_trades": st("unevaluable_trades"),
         "stale_mtm_trades": st("stale_mtm_trades"), "unfilled_entries": st("unfilled_entries"),
         "data_gap_exits_within_limit": st("data_gap_exits") - st("data_gap_unrealizable_exits")}
    f.update({k: sum(get(bh[p]["x1"]) for p in PERIODS) for k, get in BENCHMARK_DEFECT_KEYS.items()})
    if market is not None:
        f["duplicate_rows_same_value"] = sum((market[a].get("load_audit") or {}).get("duplicates_same_value", 0)
                                             for a in ASSETS)
    return f


def benchmark_defect_periods(bh):
    out = {}
    for p in PERIODS:
        d = {k: get(bh[p]["x1"]) for k, get in BENCHMARK_DEFECT_KEYS.items()}
        d = {k: v for k, v in d.items() if v and DATA_DEFECTS[k] == "blocking"}
        if d:
            out[p] = d
    return out


def track_status(track, bad_periods):
    """pass | fail (aspoň jedno porušené kritérium nezávislé na vadném benchmarku) | unknown."""
    failing = [c for c, ok in track.items() if not ok]
    if not failing:
        return "pass", []
    reliable = [c for c in failing if not (set(BENCHMARK_DEPENDENCY.get(c, tuple(PERIODS))) & set(bad_periods))]
    return ("fail", reliable) if reliable else ("unknown", failing)


def final_verdict(track_a, track_b, robust, flags, bench_bad_periods=None, latency_val_x2_net=1.0):
    """Datová brána na úrovni finálního verdiktu (kolo 6 bod 3, kolo 8 bod 1); latence +5 min je samostatná nedatová
    podmínka kandidáta. Robustnost benchmark nepoužívá ⇒ její selhání = ZAMÍTNUTO. Vrací (verdikt, blokující, detail)."""
    bad = dict(bench_bad_periods or {})
    blocking = blocking_defects(flags)
    sa, sb = track_status(track_a, bad), track_status(track_b, bad)
    detail = {"track_a": sa[0], "track_b": sb[0], "track_a_reasons": sa[1], "track_b_reasons": sb[1],
              "benchmark_defect_periods": bad, "robust": all(robust.values()), "latency_val_x2_net": latency_val_x2_net}
    if not all(robust.values()):
        return "ZAMÍTNUTO", blocking, detail
    if "pass" in (sa[0], sb[0]):
        if blocking or latency_val_x2_net <= 0:
            why = ", ".join(sorted(blocking)) + ("" if latency_val_x2_net > 0 else (", " if blocking else "") + "latence +5 min")
            return "NEROZHODNUTO — datové závady nebo ztráta při latenci +5 min: " + why, blocking, detail
        return "KANDIDÁT NA FORWARD PAPER", blocking, detail
    if "unknown" in (sa[0], sb[0]):
        crit = set(sa[1] if sa[0] == "unknown" else []) | set(sb[1] if sb[0] == "unknown" else [])
        return "NEROZHODNUTO — zamítnutí stojí jen na kritériích s vadným benchmarkem: " + ", ".join(sorted(crit)), \
            blocking, detail
    return "ZAMÍTNUTO", blocking, detail


LOCK_FILE = ".run.lock"


def atomic_write(path, data):
    """Kolo 8, bod 5: zápis přes dočasný soubor a os.replace (text i bytes)."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_bytes(data) if isinstance(data, bytes) else tmp.write_text(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


class RunLock:
    """Výhradní zámek výstupního adresáře (O_EXCL). Souběžný běh ⇒ exit 5 ještě před načtením dat."""
    def __init__(self, outdir):
        self.path = Path(outdir) / LOCK_FILE

    def __enter__(self):
        try:
            fd_ = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            print("RUN_REFUSED", f"výstupní adresář je zamčen jiným během ({self.path})")
            sys.exit(5)
        os.write(fd_, str(os.getpid()).encode())
        os.close(fd_)
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
        return False


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_audit_bundle(outdir):
    out = Path(outdir)
    man = json.loads((out / AUDIT_MANIFEST_FILE).read_text())
    bad = [f for f, h in man.get("files_sha256", {}).items() if not (out / f).exists() or file_sha256(out / f) != h]
    return (not bad), bad


def audit_manifest(outdir, produced, data_fp, run_id=None):
    out = Path(outdir)
    return {"mode": "audit", "run_id": run_id, "run_utc": datetime.now(timezone.utc).isoformat(),
            "produced_by_this_run": list(produced),
            "files_sha256": {f: file_sha256(out / f) for f in produced if f != AUDIT_MANIFEST_FILE and (out / f).exists()},
            "impl_sha256": impl_fingerprint(), "data_manifest_sha256": data_fp,
            "preexisting_performance_files_not_from_this_run": [f for f in PERFORMANCE_FILES if (out / f).exists()],
            "note": "audit nepočítá výkonnost; případné results.json/trades.csv nejsou výstupem tohoto běhu"}


REQUEST_MODES = {"AUDIT": "audit", "PERF": "perf"}


def mode_from_request(path):
    """Whitelist režimů (kolo 6, bod 5): první slovo RUN_REQUEST AUDIT nebo PERF, jinak exit 4."""
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
            "neighbors_val_x2_profit": all(v > 0 for v in nb.values()), "walk_forward_ge_3_of_4": wf_pos >= 3}


def funding_audit(m):
    """Přechody funding_interval_hours a nesoulady rozestupu pro sémantiku A (interval od události k další)
    a B (interval úseku končícího událostí). Jen diagnostika; rozhoduje člověk z konkrétních přechodů."""
    fts = m["fts"]
    trans, mis_a, mis_b, mis_bt = [], 0, 0, 0
    for k in range(len(fts) - 1):
        sp = (fts[k + 1] - fts[k]) / HOUR_MS
        ia, ib = m["finterval"][fts[k]], m["finterval"][fts[k + 1]]
        mis_a += sp != ia
        mis_b += sp != ib
        mis_bt += not spacing_ok(fts[k], ia, fts[k + 1], ib)
        if ia != ib:
            trans.append({"at": iso(fts[k + 1]), "from_h": ia, "to_h": ib, "spacing_h": sp,
                          "context": [(iso(fts[j]), m["finterval"][fts[j]]) for j in range(max(0, k - 2), min(len(fts), k + 4))]})
    return {"funding_events": len(fts), "interval_transitions": trans,
            "spacing_mismatch_semantics_A": mis_a, "spacing_mismatch_semantics_B": mis_b,
            "spacing_mismatch_semantics_B_tolerant_implemented": mis_bt}


def latency_info(market, chosen, ctag):
    """Informativní citlivost na latenci +5 min (vstup o svíčku později)."""
    return {p: {f"x{m}": run(market, pdate(PERIODS[p][0]), pdate(PERIODS[p][1]), m, chosen[0], chosen[1],
                             ctag + "_lat5m", delay_bars=1)[0] for m in (1, 2)} for p in ("validation", "final_test")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-5m")
    ap.add_argument("--outdir", default="research/spot_led")
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
    if mode is None:  # kolo 6, bod 5: režim musí být explicitní
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
        if not ok:  # data načtena, simulace nesmí proběhnout; nic se nezapisuje
            print("PERFORMANCE_REFUSED", why)
            sys.exit(3)
    atomic_write(out / "data_source.json", json.dumps({"run_id": run_id, "archives": manifest, "missing": missing,
                                                       "data_manifest_sha256": data_fp}, indent=1))
    if fatal:
        print("FATAL missing archives after first available month", json.dumps(fatal[:30]))
        sys.exit(2)
    audit = {a: gap_audit(market[a]) for a in ASSETS}
    print("GAP_AUDIT", json.dumps(audit))
    fa = {a: funding_audit(market[a]) for a in ASSETS}
    atomic_write(out / "data_audit.json", json.dumps({"gaps": audit, "funding": fa,
                                                      "load_audit": {a: market[a].get("load_audit") for a in ASSETS}},
                                                     indent=1, default=str))
    if mode == "audit":
        man = audit_manifest(out, ("data_source.json", "data_audit.json", AUDIT_MANIFEST_FILE), data_fp, run_id)
        atomic_write(out / AUDIT_MANIFEST_FILE, json.dumps(man, indent=1))  # zapisuje se poslední, s hashi souborů
        print("AUDIT_MANIFEST", json.dumps(man))
        return

    rows, results, tune, rets_store = [], {}, {}, {}
    for (th, hold) in GRID:
        tag = vt(th, hold)
        results[tag] = {}
        for p, (s, e) in PERIODS.items():
            results[tag][p] = {}
            for m in COST_MULTIPLIERS:
                r, trades, rets = run(market, pdate(s), pdate(e), m, th, hold, tag)
                results[tag][p][f"x{m}"] = r
                rets_store[(tag, p, m)] = rets
                rows += [trade_row(p, t) for t in trades]
        tune[tag] = results[tag]["tuning"]["x1"]
    chosen = max(GRID, key=lambda g: (tune[vt(*g)]["net_pnl"], -GRID.index(g)))
    ctag = vt(*chosen)
    bh = {p: {f"x{m}": buy_hold(market, pdate(s), pdate(e), m) for m in COST_MULTIPLIERS}
          for p, (s, e) in PERIODS.items()}
    wf = {}
    for y in WF_YEARS:
        r, trades, _ = run(market, date(y, 1, 1), date(y, 12, 31), 2, chosen[0], chosen[1], ctag)
        wf[str(y)] = r
        rows += [trade_row(f"wf_{y}", t) for t in trades]

    res = results[ctag]
    track_a, track_b = evaluate(res, bh)
    passed_a, passed_b = all(track_a.values()), all(track_b.values())
    vrets = rets_store[(ctag, "validation", 1)]
    dsr = safe_dsr(vrets, DSR_N, DSR_VAR_ANNUAL)
    dsr_sens = {f"N{n}_V{v}": safe_dsr(vrets, n, v)["dsr"] for n in (159, 318, 636) for v in (0.5, 1.0, 2.0)}
    latency = latency_info(market, chosen, ctag)
    nb = {vt(*g): results[vt(*g)]["validation"]["x2"]["net_pnl"] for g in neighbors(*chosen)}
    robust = robustness_checks(dsr, nb, wf)
    flags = defect_flags(res, bh, market)
    verdict, blocking, verdict_detail = final_verdict(track_a, track_b, robust, flags, benchmark_defect_periods(bh),
                                                      latency["validation"]["x2"]["net_pnl"])
    payload = {"protocol": "research/spot_led/PROTOCOL.md", "chosen": ctag, "tuning_selection_x1": tune,
               "strategy": results, "buy_hold_equal_3": bh, "walk_forward_x2": wf, "neighbors_val_x2": nb,
               "track_a": track_a, "track_b": track_b, "passed_a": passed_a, "passed_b": passed_b,
               "dsr_validation_x1": dsr,
               "dsr_note": "N = 159 je pracovní odhad (ne doložená horní mez); V[SR] = 0,5 p.a. je předpoklad",
               "dsr_sensitivity_scenarios": dsr_sens, "latency_plus_5m_info": latency,
               "walk_forward_note": "roční stabilita fixní varianty vybrané na 2020-02…2022; pro 2021–22 NE čistý OOS",
               "robustness": robust, "gap_audit": audit, "data_defect_flags": flags,
               "blocking_data_defects": blocking, "data_defect_classes": DATA_DEFECTS,
               "verdict_detail": verdict_detail, "benchmark_dependency": BENCHMARK_DEPENDENCY, "run_id": run_id,
               "impl_sha256": impl_fingerprint(), "data_manifest_sha256": data_fp, "verdict": verdict}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else ["period"])
    w.writeheader()
    w.writerows(rows)
    data = buf.getvalue().encode()
    if len(data) > 50 * 2 ** 20:  # limit souborů GitHubu
        import gzip
        name = "trades.csv.gz"
        atomic_write(out / name, gzip.compress(data))
        (out / "trades.csv").unlink(missing_ok=True)
    else:
        name = "trades.csv"
        atomic_write(out / name, data)
        (out / "trades.csv.gz").unlink(missing_ok=True)
    payload["trades_file"], payload["trades_sha256"] = name, file_sha256(out / name)
    atomic_write(out / "results.json", json.dumps(payload, indent=1, default=str))  # poslední, váže soubor obchodů
    print("SUMMARY", json.dumps({"chosen": ctag, "verdict": verdict, "track_a": track_a, "track_b": track_b,
                                 "robust": robust, "dsr": dsr["dsr"], "dsr_sens": dsr_sens, "neighbors": nb,
                                 "latency_val_x2": latency["validation"]["x2"]["net_pnl"],
                                 "val": res["validation"], "final": res["final_test"], "tuning": res["tuning"],
                                 "bh_val": bh["validation"]["x1"], "bh_final": bh["final_test"]["x2"],
                                 "wf": {k: v["net_pnl"] for k, v in wf.items()}}, default=str))


if __name__ == "__main__":
    main()
