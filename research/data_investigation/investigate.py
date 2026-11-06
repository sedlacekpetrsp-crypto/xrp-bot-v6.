"""Kolo 10: vyšetření mezer v archivech Binance Vision (PAPER výzkum, jen čtení veřejných dat, bez obchodování,
bez výpočtu výkonnosti). Výstup: report.json + gaps.csv v --outdir.

1. Přesné intervaly mezer v měsíčních archivech (1h perp 8 aktiv; 5m spot a perp BTC/ETH/XRP).
2. Pro každou mezeru denní archivy (1h/5m a 1m) a kontrolní součty .CHECKSUM ⇒ příčina (chybí v měsíčním archivu,
   chybí i v denním, chybí i v 1m).
3. Nezávislé zdroje: oficiální REST API Binance (spot/futures) a OKX — stav odpovědi a počet svíček v intervalu.
4. Point-in-time univerzum USDT-M perpů z výpisu bucketu (první/poslední měsíc fundingu, včetně delistovaných).
5. Mark price vs last price v časech fundingu (1h, 8 aktiv, 2023–2024).
6. Exekuce spot-led: XRPUSDT perp aggTrades v 6 předem určených dnech, po 5m spotovém pohybu ≥ 0,2 %.
"""
import argparse, csv, hashlib, io, json, re, sys, time, urllib.error, urllib.request, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

V = "https://data.binance.vision"
H, M5 = 3_600_000, 300_000
UA = {"User-Agent": "paper-research-gap-investigation/1.0"}
PERP8 = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT")
SL3 = ("BTCUSDT", "ETHUSDT", "XRPUSDT")
LOG = []


def get(url, timeout=120, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception as e:  # síť
            if k == tries - 1:
                return f"ERR {type(e).__name__}: {e}", b""
            time.sleep(2 + 3 * k)


def cached(cache, url):
    p = Path(cache) / hashlib.sha1(url.encode()).hexdigest()
    if p.exists():
        return 200, p.read_bytes()
    st, b = get(url)
    if st == 200:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    return st, b


def ms(x):
    x = int(x)
    return x // 1000 if x > 10 ** 14 else x


def rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        name = z.namelist()[0]
        text = z.read(name).decode()
    out, header = [], None
    for r in csv.reader(io.StringIO(text)):
        if not r:
            continue
        if not r[0].strip().isdigit():
            header = r
            continue
        out.append(r)
    return out, header, name


def iso(t):
    return datetime.fromtimestamp(t / 1000, tz=timezone.utc).isoformat()


def months(a, b):
    y, m = a
    while (y, m) <= b:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def kline_url(market, sym, iv, tag, daily=False):
    base = f"{V}/data/spot" if market == "spot" else f"{V}/data/futures/um"
    return f"{base}/{'daily' if daily else 'monthly'}/klines/{sym}/{iv}/{sym}-{iv}-{tag}.zip"


def monthly_series(cache, market, sym, iv, first, last):
    ts, info = {}, {"files": 0, "missing_files": [], "checksum_mismatch": [], "header_files": 0, "us_ts_files": 0,
                    "out_of_month_rows": 0, "dup_rows": 0}
    for y, m in months(first, last):
        tag = f"{y}-{m:02d}"
        url = kline_url(market, sym, iv, tag)
        st, b = cached(cache, url)
        if st != 200:
            info["missing_files"].append({"month": tag, "status": st})
            continue
        info["files"] += 1
        cst, cb = get(url + ".CHECKSUM", timeout=30)
        if cst == 200 and cb.split()[0].decode() != hashlib.sha256(b).hexdigest():
            info["checksum_mismatch"].append(tag)
        rr, header, _ = rows(b)
        info["header_files"] += header is not None
        info["us_ts_files"] += any(int(r[0]) > 10 ** 14 for r in rr[:3])
        lo = int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp() * 1000)
        hi = int(datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        for r in rr:
            t = ms(r[0])
            info["out_of_month_rows"] += not (lo <= t < hi)
            info["dup_rows"] += t in ts
            ts[t] = r
    return ts, info


def gaps(ts, step):
    s = sorted(ts)
    return [(a + step, b - step, (b - a) // step - 1) for a, b in zip(s, s[1:]) if b - a > step]


def daily_count(cache, market, sym, iv, lo, hi, step):
    """Počet svíček v [lo, hi] v denních archivech (stav souborů po dnech)."""
    d, n, files = datetime.fromtimestamp(lo / 1000, tz=timezone.utc).date(), 0, {}
    end = datetime.fromtimestamp(hi / 1000, tz=timezone.utc).date()
    while d <= end:
        url = kline_url(market, sym, iv, d.isoformat(), daily=True)
        st, b = cached(cache, url)
        files[d.isoformat()] = st
        if st == 200:
            rr, _, _ = rows(b)
            n += sum(1 for r in rr if lo <= ms(r[0]) <= hi)
        d += timedelta(days=1)
    return n, files


def api_checks(sym, market, iv, lo, hi):
    out = {}
    if market == "perp":
        u = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval={iv}&startTime={lo}&endTime={hi}&limit=1500"
        okx = f"https://www.okx.com/api/v5/market/history-candles?instId={sym[:-4]}-USDT-SWAP&bar={iv.upper() if iv == '1h' else iv}&after={hi + 1}&limit=100"
    else:
        u = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={iv}&startTime={lo}&endTime={hi}&limit=1000"
        okx = f"https://www.okx.com/api/v5/market/history-candles?instId={sym[:-4]}-USDT&bar={iv.upper() if iv == '1h' else iv}&after={hi + 1}&limit=100"
    for name, url in (("binance_api", u), ("okx_api", okx)):
        st, b = get(url, timeout=30, tries=2)
        rec = {"status": st}
        if st == 200:
            try:
                j = json.loads(b)
                data = j if isinstance(j, list) else j.get("data", [])
                rec["candles_in_gap"] = sum(1 for r in data if lo <= int(r[0]) <= hi)
            except Exception as e:
                rec["parse_error"] = str(e)
        out[name] = rec
    return out


def investigate_gaps(cache):
    sets = [("perp", s, "1h", (2020, 8), (2026, 10), H) for s in PERP8] + \
           [(mk, s, "5m", (2020, 1), (2026, 10), M5) for s in SL3 for mk in ("spot", "perp")]
    table, series_info = [], {}
    for market, sym, iv, a, b, step in sets:
        ts, info = monthly_series(cache, market, sym, iv, a, b)
        series_info[f"{market}:{sym}:{iv}"] = {**info, "bars": len(ts), "first": iso(min(ts)) if ts else None,
                                               "last": iso(max(ts)) if ts else None}
        for lo, hi, n in gaps(ts, step):
            rec = {"market": market, "asset": sym, "interval": iv, "from_utc": iso(lo), "to_utc": iso(hi),
                   "expected": n, "monthly_actual": 0}
            if n <= 2000:  # denní archivy jen pro rozumně velké mezery
                rec["daily_actual"], rec["daily_files"] = daily_count(cache, market, sym, iv, lo, hi, step)
                one_m = daily_count(cache, market, sym, "1m", lo, hi + step - 60_000, 60_000)
                rec["daily_1m_actual"], rec["daily_1m_expected"] = one_m[0], (hi + step - lo) // 60_000
                if n >= 12 or iv == "1h":
                    rec["independent"] = api_checks(sym, market, iv, lo, hi)
            table.append(rec)
    for r in table:
        if r.get("daily_actual", 0) >= r["expected"]:
            r["cause"] = "chybí jen v měsíčním archivu (denní archiv je úplný) ⇒ opravitelné z denních archivů"
        elif r.get("daily_actual", 0) > 0:
            r["cause"] = "částečně v denním archivu"
        elif r.get("daily_1m_actual", 0) > 0:
            r["cause"] = "chybí v 1h/5m archivu, ale existují 1m svíčky ⇒ opravitelné agregací 1m (nutné ověřit)"
        else:
            r["cause"] = "chybí v měsíčním, denním i 1m archivu ⇒ pravděpodobně skutečně bez obchodních dat (výpadek/pauza)"
    return table, series_info


def bucket_symbols(prefix):
    syms, marker = [], ""
    while True:
        url = f"https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix={prefix}&marker={marker}"
        st, b = get(url, timeout=60)
        if st != 200:
            return syms, st
        x = b.decode()
        found = re.findall(r"<Prefix>" + re.escape(prefix) + r"([^/<]+)/</Prefix>", x)
        syms += found
        if "<IsTruncated>true</IsTruncated>" not in x or not found:
            return syms, 200
        marker = prefix + found[-1] + "/"


def bucket_files(prefix):
    keys, marker = [], ""
    while True:
        url = f"https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix={prefix}&marker={marker}"
        st, b = get(url, timeout=60)
        if st != 200:
            return keys
        found = re.findall(r"<Key>([^<]+)</Key>", b.decode())
        keys += found
        if "<IsTruncated>true</IsTruncated>" not in b.decode() or not found:
            return keys
        marker = found[-1]


def universe():
    pre = "data/futures/um/monthly/fundingRate/"
    syms, st = bucket_symbols(pre)
    out = {}
    for s in syms:
        if not s.endswith("USDT"):
            continue
        ks = [k for k in bucket_files(pre + s + "/") if k.endswith(".zip")]
        mm = sorted(re.findall(r"(\d{4}-\d{2})\.zip$", " ".join(ks)) or [m for k in ks for m in re.findall(r"(\d{4}-\d{2})\.zip", k)])
        if mm:
            out[s] = {"first": mm[0], "last": mm[-1], "months": len(mm)}
    return {"status": st, "symbols": out}


def mark_vs_last(cache):
    res = {}
    for s in PERP8:
        diffs = []
        for y, m in months((2023, 1), (2024, 12)):
            tag = f"{y}-{m:02d}"
            st1, b1 = cached(cache, f"{V}/data/futures/um/monthly/markPriceKlines/{s}/1h/{s}-1h-{tag}.zip")
            st2, b2 = cached(cache, kline_url("perp", s, "1h", tag))
            if st1 != 200 or st2 != 200:
                continue
            mk = {ms(r[0]): float(r[1]) for r in rows(b1)[0]}
            for r in rows(b2)[0]:
                t = ms(r[0])
                if (t // H) % 8 == 0 and t in mk and mk[t] > 0:
                    diffs.append((float(r[1]) / mk[t] - 1) * 1e4)  # bp: last open vs mark open
        if diffs:
            ad = sorted(abs(x) for x in diffs)
            res[s] = {"n": len(diffs), "mean_bp": sum(diffs) / len(diffs), "median_abs_bp": ad[len(ad) // 2],
                      "p99_abs_bp": ad[int(0.99 * (len(ad) - 1))], "max_abs_bp": ad[-1]}
    return res


EXEC_DAYS = ("2023-02-15", "2023-06-15", "2023-10-15", "2024-02-15", "2024-06-15", "2024-10-15")  # předem určené


def execution_sample(cache):
    out = {"days": {}, "events": []}
    for d in EXEC_DAYS:
        st_s, bs = cached(cache, kline_url("spot", "XRPUSDT", "5m", d, daily=True))
        st_p, bp = cached(cache, kline_url("perp", "XRPUSDT", "5m", d, daily=True))
        st_a, ba = cached(cache, f"{V}/data/futures/um/daily/aggTrades/XRPUSDT/XRPUSDT-aggTrades-{d}.zip")
        st_b, _ = get(f"{V}/data/futures/um/daily/bookTicker/XRPUSDT/XRPUSDT-bookTicker-{d}.zip", timeout=60)
        out["days"][d] = {"spot": st_s, "perp": st_p, "aggTrades": st_a, "bookTicker": st_b}
        if not (st_s == st_p == st_a == 200):
            continue
        spot = {ms(r[0]): (float(r[4]), float(r[5]), float(r[9])) for r in rows(bs)[0]}
        perp = {ms(r[0]): (float(r[1]), float(r[4])) for r in rows(bp)[0]}
        trades = [(ms(r[5]), float(r[1]), float(r[2]), r[6].strip().lower() == "true") for r in rows(ba)[0]]
        trades.sort()
        import bisect
        tt = [x[0] for x in trades]
        for T in sorted(spot):
            sp, pp, p = spot.get(T - M5), perp.get(T - M5), perp.get(T)
            if not (sp and pp and p) or spot[T][1] <= 0:
                continue
            rs, rp, share = spot[T][0] / sp[0] - 1, p[1] / pp[1] - 1, spot[T][2] / spot[T][1]
            side = 1 if (share > 0.65 and rs > 0.002 and rp < 0.001) else -1 if (share < 0.35 and rs < -0.002 and rp > -0.001) else 0
            if not side or (T + M5) not in perp:
                continue
            t0, op = T + M5, perp[T + M5][0]
            i = bisect.bisect_left(tt, t0)
            rec = {"day": d, "signal_utc": iso(T), "side": side, "kline_open": op,
                   "first_trade": trades[i][1] if i < len(trades) else None,
                   "first_trade_delay_ms": (trades[i][0] - t0) if i < len(trades) else None}
            for w in (1_000, 5_000, 30_000, 60_000):
                j = bisect.bisect_left(tt, t0 + w)
                q = sum(x[2] for x in trades[i:j])
                if q > 0:
                    vwap = sum(x[1] * x[2] for x in trades[i:j]) / q
                    rec[f"adverse_bp_{w // 1000}s"] = side * (vwap / op - 1) * 1e4  # + = horší než open
            out["events"].append(rec)
    ev = out["events"]
    if ev:
        for k in ("adverse_bp_1s", "adverse_bp_5s", "adverse_bp_30s", "adverse_bp_60s"):
            v = sorted(e[k] for e in ev if k in e)
            if v:
                out[f"summary_{k}"] = {"n": len(v), "mean": sum(v) / len(v), "median": v[len(v) // 2],
                                       "p90": v[int(0.9 * (len(v) - 1))]}
        out["first_trade_equals_open_share"] = sum(1 for e in ev if e["first_trade"] == e["kline_open"]) / len(ev)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/inv-cache")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    rep = {"run_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version}
    rep["gaps"], rep["series"] = investigate_gaps(a.cache)
    with open(out / "gaps.csv", "w", newline="") as fh:
        keys = ["market", "asset", "interval", "from_utc", "to_utc", "expected", "monthly_actual", "daily_actual",
                "daily_1m_actual", "daily_1m_expected", "cause"]
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rep["gaps"])
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    for name, fn in (("universe", universe), ("mark_vs_last", lambda: mark_vs_last(a.cache)),
                     ("execution", lambda: execution_sample(a.cache))):
        try:
            rep[name] = fn()
        except Exception as e:
            rep[name] = {"error": f"{type(e).__name__}: {e}"}
        (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print("DONE", len(rep["gaps"]), "gaps")


if __name__ == "__main__":
    main()
