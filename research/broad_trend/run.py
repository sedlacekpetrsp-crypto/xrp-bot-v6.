"""A2 ŠIROKÝ TREND — TS trend + vol. cílení na PIT koši USDT-M perpů (PROTOCOL.md, `b6445c5`).
PAPER výzkum, veřejná data Binance Vision, bez klíčů a objednávek.

    python -m research.broad_trend.run --cache /tmp/vision-bt --outdir research/broad_trend
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import io
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from tools.research.deflated_sharpe import dsr_from_returns  # noqa: E402

VISION = "https://data.binance.vision/data/futures/um/monthly"
LISTINGS = ROOT / "research" / "new_listing_inventory" / "listings.csv"
D0 = date(2020, 1, 1)
END_DAY = date(2026, 10, 31)
FEE, SLIP = 0.00095, 0.0005
COST_MULTIPLIERS = (0, 1, 2, 3)
GRID = [(w, m) for w in (50, 100) for m in ("LO", "LS")]
BLOCKS = {"tuning": (date(2020, 6, 1), date(2022, 9, 22)),
          "validation": (date(2023, 1, 1), date(2024, 9, 22)),
          "final_test": (date(2025, 1, 1), date(2026, 10, 31))}
WF_YEARS = (2021, 2022, 2023, 2024)
START_EQUITY = 10_000.0
TOP_N, MIN_AGE, COVERAGE, VOL_WIN, QV_WIN = 50, 120, 0.90, 30, 30
VOL_TARGET, W_CAP, GROSS_CAP, MIN_NOTIONAL = 0.40, 0.10, 1.0, 5.0
LIQ_MULT = 2.0
DSR_N, DSR_VAR_ANNUAL = 214, 0.5
DAY_MS = 86_400_000
EPOCH = date(1970, 1, 1)


def vname(w, m):
    return f"W{w}_{m}"


def di(d):
    return (d - D0).days


def dd(i):
    return D0 + timedelta(days=i)


ND = di(END_DAY) + 1


def _ms(ts):
    return ts // 1000 if ts > 10 ** 14 else ts


# ------------------------------------------------------------------ data
def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&%._-~"),
                                         headers={"User-Agent": "paper-research/1.0"})
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
    """→ {day_idx: (open, high, low, close, volume, quote_volume)}"""
    out = {}
    for r in _csv_rows(payload):
        d = EPOCH + timedelta(days=_ms(int(r[0])) // DAY_MS)
        out[di(d)] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[7]))
    return out


def parse_funding(payload):
    """→ {day_idx: součet sazeb toho dne}"""
    out = {}
    for r in _csv_rows(payload):
        d = EPOCH + timedelta(days=_ms(int(r[0])) // DAY_MS)
        out[di(d)] = out.get(di(d), 0.0) + float(r[2])
    return out


def month_range(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def get_verified(url, cache, fetcher=None):
    fetcher = fetcher or fetch
    p = Path(cache) / url.split("/monthly/", 1)[1]
    if p.exists():
        payload = p.read_bytes()
    else:
        payload = fetcher(url)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    cp = p.with_name(p.name + ".CHECKSUM")
    try:
        if cp.exists():
            expected = cp.read_text().split()[0].lower()
        else:
            raw = fetcher(url + ".CHECKSUM").decode()
            cp.write_text(raw)
            expected = raw.split()[0].lower()
        status = "ok" if expected == sha else "MISMATCH"
    except urllib.error.HTTPError:
        status = "missing"
    return payload, sha, status


def load_listings(path=LISTINGS):
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["reused_ticker"] == "True":
                continue
            out.append({"symbol": r["symbol"], "first": date.fromisoformat(r["first_day"]),
                        "last": min(date.fromisoformat(r["last_day"]), END_DAY)})
    return sorted(out, key=lambda x: x["symbol"])


def _load_months(sym, kind, start, end, cache, fetcher):
    data, manifest, missing = {}, [], []
    for y, m in month_range(start, end):
        tag = f"{y}-{m:02d}"
        if kind == "kl":
            url = f"{VISION}/klines/{sym}/1d/{sym}-1d-{tag}.zip"
        else:
            url = f"{VISION}/fundingRate/{sym}/{sym}-fundingRate-{tag}.zip"
        try:
            payload, sha, st = get_verified(url, cache, fetcher)
        except urllib.error.HTTPError as e:
            missing.append({"symbol": sym, "kind": kind, "month": tag, "http": e.code})
            continue
        except Exception as e:  # síť po opakováních
            missing.append({"symbol": sym, "kind": kind, "month": tag, "error": str(e)[:80]})
            continue
        manifest.append({"url": url, "sha256": sha, "checksum": st})
        part = parse_klines(payload) if kind == "kl" else parse_funding(payload)
        if kind == "fr":
            for k, v in part.items():
                data[k] = data.get(k, 0.0) + v
        else:
            data.update(part)
    return data, manifest, missing


# ------------------------------------------------------------------ series
class Series:
    """Denní svíčky jednoho kontraktu v poli podle indexu dne; obchodní den = objem > 0."""

    def __init__(self, symbol, bars, first, last, funding=None):
        self.symbol = symbol
        self.first_i = di(first)
        self.last_i = di(last)
        self.close = [None] * ND
        self.high = [None] * ND
        trade = [0] * (ND + 1)
        qv = [0.0] * (ND + 1)
        for i, b in bars.items():
            if 0 <= i < ND and b[4] > 0:
                self.close[i], self.high[i] = b[3], b[1]
                trade[i + 1], qv[i + 1] = 1, b[5]
        for i in range(ND):  # prefixové součty
            trade[i + 1] += trade[i]
            qv[i + 1] += qv[i]
        self._trade, self._qv = trade, qv
        self.funding = funding or {}

    def trading(self, i):
        return 0 <= i < ND and self.close[i] is not None

    def n_trading(self, a, b):
        """Počet obchodních dní v [a, b]."""
        a, b = max(a, 0), min(b, ND - 1)
        return 0 if b < a else self._trade[b + 1] - self._trade[a]

    def qv_sum(self, a, b):
        a, b = max(a, 0), min(b, ND - 1)
        return 0.0 if b < a else self._qv[b + 1] - self._qv[a]

    def close_asof(self, i):
        while i >= 0:
            if self.close[i] is not None:
                return self.close[i]
            i -= 1
        return None


# ------------------------------------------------------------------ PIT univerzum a signál (jen data ≤ R−1)
def universe(series_list, r, w):
    """Top 50 kandidátů podle průměrného quote objemu za 30 dní do R−1."""
    p = r - 1
    cands = []
    for s in series_list:
        if not s.trading(p) or r - s.first_i < MIN_AGE or p > s.last_i:
            continue
        if s.n_trading(p - w, p) < COVERAGE * (w + 1):
            continue
        cands.append((-s.qv_sum(p - QV_WIN + 1, p) / QV_WIN, s.symbol, s))
    cands.sort(key=lambda x: (x[0], x[1]))
    return [c[2] for c in cands[:TOP_N]]


def vol_annual(s, p):
    px = [s.close[i] for i in range(p - VOL_WIN, p + 1) if s.close[i] is not None]
    lr = [math.log(px[k] / px[k - 1]) for k in range(1, len(px))]
    if len(lr) < 10:
        return None
    m = sum(lr) / len(lr)
    sd = math.sqrt(sum((x - m) ** 2 for x in lr) / (len(lr) - 1))
    return sd * math.sqrt(365) if sd > 0 else None


def target_weights(series_list, r, w, mode):
    """→ ({symbol: váha}, univerzum). Jen data ≤ R−1."""
    uni = universe(series_list, r, w)
    n = len(uni)
    out = {}
    for s in uni:
        p = r - 1
        c0 = s.close_asof(p - w)
        sig = 0
        if c0:
            ret = s.close[p] / c0 - 1.0
            sig = 1 if ret > 0 else (-1 if ret < 0 else 0)
        if mode == "LO" and sig < 0:
            sig = 0
        if sig == 0:
            continue
        vol = vol_annual(s, p)
        if not vol:
            continue
        out[s.symbol] = max(-W_CAP, min(W_CAP, sig * (VOL_TARGET / vol) / n))
    g = sum(abs(x) for x in out.values())
    if g > GROSS_CAP:
        out = {k: v * GROSS_CAP / g for k, v in out.items()}
    return out, uni


def exposure_matched(weights, uni):
    g = sum(abs(x) for x in weights.values())
    return {s.symbol: g / len(uni) for s in uni} if uni and g > 0 else {}


def ew_basket(uni):
    return {s.symbol: 1.0 / len(uni) for s in uni} if uni else {}


# ------------------------------------------------------------------ simulace portfolia
def simulate(series_map, start, end, weight_fn, mult, book="strategy"):
    """weight_fn(r_idx) → {symbol: váha}; rebalance v pondělí, fill za close R. → (equity [(den, E)], epizody)."""
    c = (FEE + SLIP) * mult
    a, b = di(start), di(end)
    E = START_EQUITY
    pos = {}  # sym → dict(qty, last, fill, ep)
    episodes, curve = [], []
    stats = {"liquidations": 0, "forced_exits": 0, "turnover": 0.0, "gross_exposure": []}

    def open_ep(sym, side, t):
        return {"book": book, "symbol": sym, "side": side, "entry_day": dd(t).isoformat(), "exit_day": None,
                "price_pnl": 0.0, "funding": 0.0, "cost": 0.0, "exit_reason": None}

    def close_ep(sym, t, reason):
        ep = pos[sym]["ep"]
        ep["exit_day"], ep["exit_reason"] = dd(t).isoformat(), reason
        ep["net_pnl"] = ep["price_pnl"] + ep["funding"] - ep["cost"]
        episodes.append(ep)
        del pos[sym]

    for t in range(a, b + 1):
        # 1) mark-to-market, funding, likvidace, nucené výstupy (stávající qty)
        for sym in list(pos):
            s, p = series_map[sym], pos[sym]
            if not s.trading(t) or t > s.last_i:
                cost = abs(p["qty"]) * p["last"] * c
                E -= cost
                p["ep"]["cost"] += cost
                stats["turnover"] += abs(p["qty"]) * p["last"]
                stats["forced_exits"] += 1
                close_ep(sym, t, "forced_exit")
                continue
            if p["qty"] < 0 and s.high[t] >= LIQ_MULT * p["fill"]:
                liq_px = LIQ_MULT * p["fill"]
                d_pnl = p["qty"] * (liq_px - p["last"])
                E += d_pnl
                p["ep"]["price_pnl"] += d_pnl
                stats["liquidations"] += 1
                close_ep(sym, t, "liquidation")
                continue
            d_pnl = p["qty"] * (s.close[t] - p["last"])
            p["last"] = s.close[t]
            E += d_pnl
            p["ep"]["price_pnl"] += d_pnl
            rate = s.funding.get(t)
            if rate is not None:
                f = -p["qty"] * rate * s.close[t]
                E += f
                p["ep"]["funding"] += f
        last_day = t == b
        # 2) rebalance (pondělí) nebo uzavření na konci bloku
        if dd(t).weekday() == 0 and not last_day:
            tw = weight_fn(t)
            stats["gross_exposure"].append(sum(abs(x) for x in tw.values()))
            targets = {}
            for sym, w in tw.items():
                s = series_map[sym]
                if not s.trading(t):
                    continue
                notional = w * E
                if abs(notional) >= MIN_NOTIONAL:
                    targets[sym] = notional / s.close[t]
            for sym in sorted(set(pos) | set(targets)):
                s = series_map[sym]
                px = s.close[t]
                old = pos[sym]["qty"] if sym in pos else 0.0
                new = targets.get(sym, 0.0)
                if old and abs(new - old) * px < MIN_NOTIONAL and (new > 0) == (old > 0) and new != 0:
                    continue
                if old and (new == 0 or (new > 0) != (old > 0)):  # uzavření / otočení
                    cost = abs(old) * px * c
                    E -= cost
                    pos[sym]["ep"]["cost"] += cost
                    stats["turnover"] += abs(old) * px
                    close_ep(sym, t, "rebalance")
                    old = 0.0
                if new == 0:
                    continue
                cost = abs(new - old) * px * c
                E -= cost
                stats["turnover"] += abs(new - old) * px
                if sym not in pos:
                    pos[sym] = {"qty": 0.0, "last": px, "fill": px, "ep": open_ep(sym, "long" if new > 0 else "short", t)}
                p = pos[sym]
                p["ep"]["cost"] += cost
                if abs(new) > abs(old):  # likvidační cena podle průměrného fillu
                    p["fill"] = (abs(old) * p["fill"] + abs(new - old) * px) / abs(new)
                p["qty"], p["last"] = new, px
        elif last_day:
            for sym in sorted(pos):
                p = pos[sym]
                cost = abs(p["qty"]) * p["last"] * c
                E -= cost
                p["ep"]["cost"] += cost
                stats["turnover"] += abs(p["qty"]) * p["last"]
                close_ep(sym, t, "block_end")
        curve.append((dd(t).isoformat(), E))
    return curve, episodes, stats


def btc_bh(btc, start, end):
    a, b = di(start), di(end)
    c0 = btc.close_asof(a)
    q = START_EQUITY / c0
    return [(dd(t).isoformat(), q * btc.close_asof(t)) for t in range(a, b + 1)]


# ------------------------------------------------------------------ metriky
def curve_metrics(curve):
    eq = [START_EQUITY] + [e for _, e in curve]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq)) if eq[i - 1] > 0]
    mdd, peak = 0.0, eq[0]
    for e in eq:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak if peak > 0 else 0)
    sh = None
    if len(rets) > 2:
        m = sum(rets) / len(rets)
        sd = math.sqrt(sum((x - m) ** 2 for x in rets) / (len(rets) - 1))
        sh = round(m / sd * math.sqrt(365), 4) if sd > 0 else None
    return {"net_pnl": round(eq[-1] - START_EQUITY, 4), "return_pct": round((eq[-1] / START_EQUITY - 1) * 100, 4),
            "sharpe": sh, "max_dd_pct": round(mdd * 100, 4)}, rets


def summarize(curve, episodes, stats):
    m, rets = curve_metrics(curve)
    pnl = [e["net_pnl"] for e in episodes]
    pos_, neg = sum(x for x in pnl if x > 0), -sum(x for x in pnl if x < 0)
    srt = sorted(pnl, reverse=True)
    ge = stats["gross_exposure"]
    m.update({
        "trades": len(pnl), "pf": round(pos_ / neg, 4) if neg > 0 else None,
        "net_ex_top3": round(sum(srt[3:]), 4),
        "top5_share": round(sum(srt[:5]) / sum(pnl), 4) if pnl and sum(pnl) > 0 else None,
        "episode_pnl_sum": round(sum(pnl), 4),
        "price_pnl": round(sum(e["price_pnl"] for e in episodes), 4),
        "funding": round(sum(e["funding"] for e in episodes), 4),
        "cost": round(sum(e["cost"] for e in episodes), 4),
        "liquidations": stats["liquidations"], "forced_exits": stats["forced_exits"],
        "turnover": round(stats["turnover"], 2),
        "avg_gross_exposure": round(sum(ge) / len(ge), 4) if ge else 0.0,
    })
    return m, rets


# ------------------------------------------------------------------ hlavní běh
def build_data(cache, outdir, workers=32, fetcher=None):
    listings = load_listings()
    manifest, missing = [], []
    series = {}

    def job_kl(l):
        return l, _load_months(l["symbol"], "kl", l["first"], l["last"], cache, fetcher)

    t0 = time.time()
    with cf.ThreadPoolExecutor(workers) as ex:
        for k, (l, (bars, man, mis)) in enumerate(ex.map(job_kl, listings)):
            manifest += man
            missing += mis
            series[l["symbol"]] = Series(l["symbol"], bars, l["first"], l["last"])
            if k % 100 == 0:
                print(f"klines {k}/{len(listings)} {time.time() - t0:.0f}s", flush=True)
    return listings, series, manifest, missing


def ever_in_universe(series, blocks_all):
    sl = list(series.values())
    need = {}
    for (a, b) in blocks_all:
        for t in range(di(a), di(b) + 1):
            if dd(t).weekday() != 0:
                continue
            for w, _ in GRID:
                for s in universe(sl, t, w):
                    lo, hi = need.get(s.symbol, (t, t))
                    need[s.symbol] = (min(lo, t), max(hi, t))
    return need


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-bt")
    ap.add_argument("--outdir", default="research/broad_trend")
    a = ap.parse_args(argv)
    out = Path(a.outdir)
    listings, series, manifest, missing = build_data(a.cache, out)
    n_kl = len(manifest) + sum(1 for m in missing if m["kind"] == "kl")
    kl_missing = sum(1 for m in missing if m["kind"] == "kl")
    blocks_all = list(BLOCKS.values()) + [(date(y, 1, 1), date(y, 12, 31)) for y in WF_YEARS]
    need = ever_in_universe(series, blocks_all)
    print(f"symbols ever in universe: {len(need)}", flush=True)

    def job_fr(sym):
        lo, hi = need[sym]
        return sym, _load_months(sym, "fr", dd(lo), min(dd(hi + 45), END_DAY), a.cache, None)

    with cf.ThreadPoolExecutor(32) as ex:
        for sym, (fund, man, mis) in ex.map(job_fr, sorted(need)):
            manifest += man
            missing += mis
            series[sym].funding = fund
    bad_sha = sum(1 for m in manifest if m["checksum"] == "MISMATCH")
    valid_run = kl_missing <= 0.02 * max(n_kl, 1) and bad_sha == 0
    (out / "data_source.json").write_text(json.dumps({
        "protocol": "research/broad_trend/PROTOCOL.md", "archives": len(manifest),
        "checksum_ok": sum(1 for m in manifest if m["checksum"] == "ok"), "checksum_mismatch": bad_sha,
        "missing": missing, "manifest": manifest}, indent=0))
    results = {"protocol_commit": "b6445c5", "valid_run": valid_run, "kl_archives": n_kl, "kl_missing": kl_missing,
               "symbols": len(listings), "symbols_ever_in_universe": len(need),
               "costs": {"fee": FEE, "slip": SLIP}, "dsr": {"n": DSR_N, "var_annual": DSR_VAR_ANNUAL},
               "variants": {}, "benchmarks": {}}
    if not valid_run:
        (out / "results.json").write_text(json.dumps(results, indent=1))
        print("INVALID RUN (data)", kl_missing, bad_sha)
        return 2
    sl = sorted(series.values(), key=lambda s: s.symbol)
    btc = series["BTCUSDT"]
    trade_rows, equity_rows, vrets = [], {}, {}
    wcache = {}

    def weights(t, w, mode):
        key = (t, w, mode)
        if key not in wcache:
            wcache[key] = target_weights(sl, t, w, mode)
        return wcache[key]

    block_list = list(BLOCKS.items()) + [(f"wf{y}", (date(y, 1, 1), date(y, 12, 31))) for y in WF_YEARS]
    for (w, mode) in GRID:
        v = vname(w, mode)
        res_v = results["variants"].setdefault(v, {})
        for bname, (s0, s1) in block_list:
            for mlt in COST_MULTIPLIERS:
                if bname.startswith("wf") and mlt != 2:
                    continue
                books = {
                    "strategy": lambda t, w=w, mode=mode: weights(t, w, mode)[0],
                    "exposure_matched": lambda t, w=w, mode=mode: exposure_matched(*weights(t, w, mode)),
                    "ew_basket": lambda t, w=w, mode=mode: ew_basket(weights(t, w, mode)[1]),
                }
                cell = {}
                for book, fn in books.items():
                    curve, eps, st = simulate(series, s0, s1, fn, mlt, book)
                    summ, rets = summarize(curve, eps, st)
                    cell[book] = summ
                    if book == "strategy":
                        vrets[(v, bname, mlt)] = rets
                    if bname in BLOCKS and mlt in (1, 2, 3) and book in ("strategy", "exposure_matched"):
                        for e in eps:
                            trade_rows.append({"variant": v, "block": bname, "mult": mlt, **e})
                    if bname in BLOCKS and mlt in (1, 2):
                        equity_rows[(v, bname, mlt, book)] = curve
                res_v[f"{bname}_x{mlt}"] = cell
            print(f"{v} {bname} done", flush=True)
    for bname, (s0, s1) in block_list:
        curve = btc_bh(btc, s0, s1)
        results["benchmarks"][bname] = {"btc_bh": curve_metrics(curve)[0]}
        if bname in BLOCKS:
            equity_rows[("BTC", bname, 0, "btc_bh")] = curve

    # výběr na ladění ×1 podle Sharpe
    order = [vname(w, m) for w, m in GRID]
    chosen = max(order, key=lambda v: (results["variants"][v]["tuning_x1"]["strategy"]["sharpe"] or -1e9,
                                       -order.index(v)))
    results["chosen"] = chosen
    results["criteria"] = evaluate(results, chosen, vrets)
    (out / "results.json").write_text(json.dumps(results, indent=1))
    keys = ["variant", "block", "mult", "book", "symbol", "side", "entry_day", "exit_day", "exit_reason",
            "price_pnl", "funding", "cost", "net_pnl"]
    with gzip.open(out / "trades.csv.gz", "wt", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        for r in trade_rows:
            wr.writerow({k: (round(r[k], 6) if isinstance(r[k], float) else r[k]) for k in keys})
    with open(out / "equity.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["variant", "block", "mult", "book", "day", "equity"])
        for (v, bname, mlt, book), curve in equity_rows.items():
            if v in (chosen, "BTC"):
                for d_, e in curve:
                    wr.writerow([v, bname, mlt, book, d_, round(e, 4)])
    print_summary(results)
    return 0


def neighbours(v):
    w, m = v[1:].split("_")
    return [vname(int(w), "LS" if m == "LO" else "LO"), vname(150 - int(w), m)]


def evaluate(res, v, vrets):
    R = res["variants"][v]
    val1, val2, fin2 = R["validation_x1"], R["validation_x2"], R["final_test_x2"]
    tun0, tun1 = R["tuning_x0"]["strategy"], R["tuning_x1"]["strategy"]
    fin1 = R["final_test_x1"]
    bb = res["benchmarks"]

    def gt(a, b):
        return a is not None and b is not None and a > b

    s2, em2 = val2["strategy"], val2["exposure_matched"]
    k = {}
    k["K1"] = s2["net_pnl"] > 0 and gt(s2["sharpe"], em2["sharpe"]) and s2["net_pnl"] > em2["net_pnl"]
    k["K2"] = s2["pf"] is not None and s2["pf"] > 1.2
    k["K3"] = val1["strategy"]["net_ex_top3"] > 0
    s1 = val1["strategy"]
    bh_val = [bb["validation"]["btc_bh"], val1["ew_basket"]]
    bh_fin = [bb["final_test"]["btc_bh"], fin1["ew_basket"]]
    track_a = all(gt(s1["sharpe"], x["sharpe"]) and s1["max_dd_pct"] < x["max_dd_pct"] for x in bh_val)
    track_b = (all(s1["max_dd_pct"] <= 0.6 * x["max_dd_pct"] for x in bh_val)
               and all(fin1["strategy"]["max_dd_pct"] <= 0.6 * x["max_dd_pct"] for x in bh_fin)
               and tun1["net_pnl"] > 0)
    k["K4"] = track_a or track_b
    k["K4_detail"] = {"track_a": track_a, "track_b": track_b}
    k["K5"] = fin2["strategy"]["net_pnl"] > 0 and gt(fin2["strategy"]["sharpe"], fin2["exposure_matched"]["sharpe"])
    k["K6"] = s1["trades"] >= 30
    gross = tun0["price_pnl"]
    k["K7"] = gross >= 3 * tun1["cost"]
    k["K7_detail"] = {"gross_price_pnl_x0": gross, "cost_x1": tun1["cost"]}
    d = dsr_from_returns(vrets[(v, "validation", 1)], DSR_N, DSR_VAR_ANNUAL / 365)
    k["DSR"] = round(d["dsr"], 4)
    k["neighbours_val_x2"] = {n: res["variants"][n]["validation_x2"]["strategy"]["net_pnl"] for n in neighbours(v)}
    k["walk_forward_x2"] = {y: R[f"wf{y}_x2"]["strategy"]["net_pnl"] for y in WF_YEARS}
    core = all(k[x] for x in ("K1", "K2", "K3", "K4", "K5", "K6", "K7"))
    robust = (k["DSR"] >= 0.95 and all(x > 0 for x in k["neighbours_val_x2"].values())
              and sum(1 for x in k["walk_forward_x2"].values() if x > 0) >= 3)
    k["verdict"] = "FORWARD_PAPER" if core and robust else "ZAMITNUTO"
    return k


def print_summary(res):
    v = res["chosen"]
    print(f"A2_CHOSEN {v}")
    for vv, R in res["variants"].items():
        for key in ("tuning_x1", "validation_x1", "validation_x2", "final_test_x2"):
            c = R[key]
            print(f"A2 {vv} {key} strat={c['strategy']['return_pct']:.1f}% sh={c['strategy']['sharpe']} "
                  f"dd={c['strategy']['max_dd_pct']:.1f} n={c['strategy']['trades']} | "
                  f"EM={c['exposure_matched']['return_pct']:.1f}% sh={c['exposure_matched']['sharpe']} | "
                  f"EW={c['ew_basket']['return_pct']:.1f}% sh={c['ew_basket']['sharpe']}")
    for b, x in res["benchmarks"].items():
        print(f"A2_BTC {b} {x['btc_bh']}")
    print("A2_CRITERIA", json.dumps(res["criteria"]))


if __name__ == "__main__":
    sys.exit(main())
