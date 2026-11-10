"""K3 krok 0 — datový audit dostupnosti a pokrytí historie fundingu na více burzách.

Jen metadata (časová razítka, pokrytí, mapování). Žádné statistiky hodnot fundingu. Viz PROTOCOL.md.
Použití:
  python -m research.k3_funding_audit.audit fetch --venue binance --outdir OUT
  python -m research.k3_funding_audit.audit fetch --venue hyperliquid --shard 0 --nshards 8 --outdir OUT
  python -m research.k3_funding_audit.audit combine --indir OUT --outdir research/k3_funding_audit
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
H_MS = 3_600_000
DAY_MS = 86_400_000
MIN_DAYS = 548
MIN_COV = 0.95
MIN_SYMBOLS = 20
VENUES = ("binance", "bybit", "okx", "hyperliquid")


# ---------------------------------------------------------------- mapování
def base_of(sym: str) -> str | None:
    return sym[:-4] if sym.endswith("USDT") else None


def map_symbol(sym: str, venue: str) -> str | None:
    b = base_of(sym)
    if not b:
        return None
    if venue in ("binance", "bybit"):
        return sym
    if venue == "okx":
        return f"{b}-USDT-SWAP"
    if venue == "hyperliquid":
        return "k" + b[4:] if b.startswith("1000") and len(b) > 4 else b
    raise ValueError(venue)


def load_universe(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("symbol")]


# ---------------------------------------------------------------- metriky (čisté funkce, testované)
def nominal_intervals(ts: list[int], win: int = 21) -> list[int]:
    """Nominální interval (ms, celé hodiny ≥ 1) pro každý rozdíl = modus rozdílů v okně `win` kolem něj."""
    d = [max(1, round((b - a) / H_MS)) for a, b in zip(ts, ts[1:])]
    out = []
    half = win // 2
    for i in range(len(d)):
        w = d[max(0, i - half): i + half + 1]
        c = Counter(w)
        top = max(c.values())
        out.append(min(k for k, v in c.items() if v == top) * H_MS)
    return out


def coverage(ts: list[int]) -> dict:
    ts = sorted(set(ts))
    n = len(ts)
    if n < 2:
        return {"n": n, "missing": 0, "coverage": 1.0 if n else 0.0, "interval_changes": 0, "max_gap_h": 0.0}
    nom = nominal_intervals(ts)
    missing = 0
    max_gap = 0
    for (a, b), m in zip(zip(ts, ts[1:]), nom):
        k = round((b - a) / m) - 1
        if k > 0:
            missing += k
        max_gap = max(max_gap, b - a)
    changes = sum(1 for x, y in zip(nom, nom[1:]) if x != y)
    return {"n": n, "missing": missing, "coverage": n / (n + missing), "interval_changes": changes,
            "max_gap_h": round(max_gap / H_MS, 2)}


def pair_overlap(ta: list[int], tb: list[int]) -> dict:
    if not ta or not tb:
        return {"days": 0.0, "cov_a": 0.0, "cov_b": 0.0}
    lo, hi = max(min(ta), min(tb)), min(max(ta), max(tb))
    if hi <= lo:
        return {"days": 0.0, "cov_a": 0.0, "cov_b": 0.0}
    ca = coverage([t for t in ta if lo <= t <= hi])["coverage"]
    cb = coverage([t for t in tb if lo <= t <= hi])["coverage"]
    return {"days": round((hi - lo) / DAY_MS, 1), "cov_a": round(ca, 4), "cov_b": round(cb, 4)}


def qualifies(o: dict) -> bool:
    return o["days"] >= MIN_DAYS and o["cov_a"] >= MIN_COV and o["cov_b"] >= MIN_COV


def on_hour_share(ts: list[int]) -> float:
    if not ts:
        return 0.0
    return sum(1 for t in ts if min(t % H_MS, H_MS - t % H_MS) <= 60_000) / len(ts)


# ---------------------------------------------------------------- HTTP
class Pacer:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.next_t = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next_t)
            self.next_t = t + self.min_interval
        if t > now:
            time.sleep(t - now)


STATUS = Counter()


def http(url: str, pacer: Pacer, data: bytes | None = None, tries: int = 6):
    hdr = {"User-Agent": "xrp-bot-v6-research-k3-audit/1.0"}
    if data is not None:
        hdr["Content-Type"] = "application/json"
    for i in range(tries):
        pacer.wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdr), timeout=60) as r:
                STATUS[r.status] += 1
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            STATUS[e.code] += 1
            if e.code in (429, 418) or e.code >= 500:
                time.sleep(min(60, 2 ** i * 2))
                continue
            return e.code, b""
        except Exception:  # síť
            STATUS["neterr"] += 1
            time.sleep(min(60, 2 ** i * 2))
    return -1, b""


# ---------------------------------------------------------------- fetchery: vrací list[(ts_ms, rate_str)] nebo None (neexistuje)
def months(d0: str, d1: str):
    a = date.fromisoformat(d0[:10]).replace(day=1)
    b = date.fromisoformat(d1[:10]).replace(day=1)
    while a <= b:
        yield f"{a.year:04d}-{a.month:02d}"
        a = date(a.year + (a.month == 12), a.month % 12 + 1, 1)


def fetch_binance(row: dict, pacer: Pacer):
    s = row["symbol"]
    out = []
    for m in months(row["first_day"], row["last_day"]):
        url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"
        code, body = http(url, pacer)
        if code != 200:
            continue
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            for name in z.namelist():
                for r in csv.reader(io.TextIOWrapper(z.open(name))):
                    if r and r[0].isdigit():
                        out.append((int(r[0]), r[-1]))
    return out or None


def fetch_bybit(row: dict, pacer: Pacer):
    s = map_symbol(row["symbol"], "bybit")
    out, end = [], None
    while True:
        url = f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={s}&limit=200"
        if end:
            url += f"&endTime={end}"
        code, body = http(url, pacer)
        if code != 200:
            return out or None
        j = json.loads(body)
        lst = (j.get("result") or {}).get("list") or []
        if j.get("retCode") != 0 or not lst:
            return out or None
        out += [(int(x["fundingRateTimestamp"]), x["fundingRate"]) for x in lst]
        oldest = min(int(x["fundingRateTimestamp"]) for x in lst)
        if end is not None and oldest >= end:
            return out
        end = oldest - 1


def fetch_okx(row: dict, pacer: Pacer):
    s = map_symbol(row["symbol"], "okx")
    out, after = [], None
    while True:
        url = f"https://www.okx.com/api/v5/public/funding-rate-history?instId={s}&limit=400"
        if after:
            url += f"&after={after}"
        code, body = http(url, pacer)
        if code != 200:
            return out or None
        j = json.loads(body)
        lst = j.get("data") or []
        if j.get("code") != "0" or not lst:
            return out or None
        out += [(int(x["fundingTime"]), x.get("realizedRate") or x["fundingRate"]) for x in lst]
        after = min(int(x["fundingTime"]) for x in lst)


HL_URL = "https://api.hyperliquid.xyz/info"


def fetch_hyperliquid(row: dict, pacer: Pacer):
    coin = map_symbol(row["symbol"], "hyperliquid")
    out, start = [], 1_640_995_200_000  # 2022-01-01
    while True:
        code, body = http(HL_URL, pacer, json.dumps({"type": "fundingHistory", "coin": coin, "startTime": start}).encode())
        if code != 200:
            return out or None
        lst = json.loads(body) or []
        if not lst:
            return out or None
        out += [(int(x["time"]), x["fundingRate"]) for x in lst]
        if len(lst) < 500:
            return out
        start = int(lst[-1]["time"]) + 1


FETCH = {"binance": (fetch_binance, 0.02, 16), "bybit": (fetch_bybit, 0.06, 6),
         "okx": (fetch_okx, 0.25, 4), "hyperliquid": (fetch_hyperliquid, 2.4, 1)}


def hl_universe(pacer: Pacer) -> tuple[int, set[str]]:
    code, body = http(HL_URL, pacer, b'{"type":"meta"}')
    if code != 200:
        return code, set()
    return code, {u["name"] for u in json.loads(body).get("universe", [])}


def cmd_fetch(a):
    os.makedirs(a.outdir, exist_ok=True)
    rows = load_universe(a.universe)
    fn, gap, workers = FETCH[a.venue]
    pacer = Pacer(gap)
    meta = {"venue": a.venue, "shard": a.shard, "nshards": a.nshards, "started": datetime.now(timezone.utc).isoformat()}
    if a.venue == "hyperliquid":
        code, uni = hl_universe(pacer)
        meta["meta_http"] = code
        meta["hl_universe_size"] = len(uni)
        rows = [r for r in rows if map_symbol(r["symbol"], "hyperliquid") in uni]
        meta["mapped_in_hl_universe"] = len(rows)
    rows = [r for i, r in enumerate(sorted(rows, key=lambda r: r["symbol"])) if i % a.nshards == a.shard]
    if a.limit:
        rows = rows[: a.limit]
    res = {}
    with ThreadPoolExecutor(workers) as ex:
        for r, data in zip(rows, ex.map(lambda r: fn(r, pacer), rows)):
            if data:
                res[r["symbol"]] = sorted(set(data))
    tag = f"{a.venue}_{a.shard}"
    with gzip.open(os.path.join(a.outdir, f"raw_{tag}.csv.gz"), "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "ts_ms", "rate"])
        for s, d in res.items():
            w.writerows((s, t, v) for t, v in d)
    meta.update({"symbols_queried": len(rows), "symbols_with_data": len(res), "http_status": dict(STATUS),
                 "finished": datetime.now(timezone.utc).isoformat()})
    with open(os.path.join(a.outdir, f"meta_{tag}.json"), "w") as f:
        json.dump({k: (str(v) if not isinstance(v, (int, float, str, dict, type(None))) else v) for k, v in meta.items()},
                  f, indent=1, default=str)
    print(json.dumps(meta, default=str))


# ---------------------------------------------------------------- combine (jen metadata)
def cmd_combine(a):
    series: dict[str, dict[str, list[int]]] = {v: {} for v in VENUES}
    metas = []
    for name in sorted(os.listdir(a.indir)):
        p = os.path.join(a.indir, name)
        if name.startswith("meta_") and name.endswith(".json"):
            metas.append(json.load(open(p)))
        if name.startswith("raw_") and name.endswith(".csv.gz"):
            v = name[4:].rsplit("_", 1)[0]
            with gzip.open(p, "rt") as f:
                for r in csv.DictReader(f):
                    series[v].setdefault(r["symbol"], []).append(int(r["ts_ms"]))
    rows = load_universe(a.universe)
    os.makedirs(a.outdir, exist_ok=True)
    per = []
    for r in rows:
        s = r["symbol"]
        for v in VENUES:
            ts = sorted(set(series[v].get(s, [])))
            if not ts:
                continue
            c = coverage(ts)
            per.append({"symbol": s, "venue": v, "first_utc": iso(ts[0]), "last_utc": iso(ts[-1]),
                        "days": round((ts[-1] - ts[0]) / DAY_MS, 1), "n": c["n"], "missing": c["missing"],
                        "coverage": round(c["coverage"], 4), "interval_changes": c["interval_changes"],
                        "max_gap_h": c["max_gap_h"], "on_hour_share": round(on_hour_share(ts), 4)})
    with open(os.path.join(a.outdir, "coverage_by_symbol_venue.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per[0].keys()) if per else ["symbol"])
        w.writeheader()
        w.writerows(per)
    pairs = [(x, y) for i, x in enumerate(VENUES) for y in VENUES[i + 1:]]
    pair_rows, qual = [], {}
    for r in rows:
        s = r["symbol"]
        for x, y in pairs:
            tx, ty = series[x].get(s), series[y].get(s)
            if not tx or not ty:
                continue
            o = pair_overlap(sorted(set(tx)), sorted(set(ty)))
            q = qualifies(o)
            pair_rows.append({"symbol": s, "pair": f"{x}-{y}", **o, "qualifies": q})
            if q:
                qual.setdefault(s, []).append(f"{x}-{y}")
    with open(os.path.join(a.outdir, "pairs_overlap.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "pair", "days", "cov_a", "cov_b", "qualifies"])
        w.writeheader()
        w.writerows(pair_rows)
    by_pair = Counter(p for ps in qual.values() for p in ps)
    with_binance = sorted(s for s, ps in qual.items() if any(p.startswith("binance-") for p in ps))
    verdict = "GO (návrh výkonnostního protokolu, výkon NESCHVÁLEN)" if len(qual) >= MIN_SYMBOLS else "DATA NO-GO"
    summary = {"universe": len(rows), "venues": {v: {"symbols_with_data": len(series[v])} for v in VENUES},
               "fetch_meta": metas, "qualifying_symbols": len(qual), "qualifying_by_pair": dict(by_pair),
               "qualifying_with_binance_leg": len(with_binance), "qualifying_list": sorted(qual),
               "gate": {"min_days": MIN_DAYS, "min_coverage": MIN_COV, "min_symbols": MIN_SYMBOLS},
               "verdict": verdict}
    with open(os.path.join(a.outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "fetch_meta"}, indent=1, default=str))


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv=None):
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fetch")
    f.add_argument("--venue", choices=VENUES, required=True)
    f.add_argument("--shard", type=int, default=0)
    f.add_argument("--nshards", type=int, default=1)
    f.add_argument("--limit", type=int, default=0)
    f.add_argument("--outdir", required=True)
    f.add_argument("--universe", default=os.path.join(HERE, "listings.csv"))
    c = sp.add_parser("combine")
    c.add_argument("--indir", required=True)
    c.add_argument("--outdir", default=HERE)
    c.add_argument("--universe", default=os.path.join(HERE, "listings.csv"))
    a = p.parse_args(argv)
    cmd_fetch(a) if a.cmd == "fetch" else cmd_combine(a)


if __name__ == "__main__":
    main()
