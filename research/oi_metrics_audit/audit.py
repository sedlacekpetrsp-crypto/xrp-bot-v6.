"""A3 krok 0 — datový audit Binance Vision `metrics` (PROTOCOL.md). Bez cen a výkonnosti.

    python -m research.oi_metrics_audit.audit --cache /tmp/vision-metrics --outdir research/oi_metrics_audit

Jen veřejná data, žádné klíče, žádné objednávky.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION = "https://data.binance.vision"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
WIN_FROM, WIN_TO = dt.date(2022, 1, 1), dt.date(2026, 10, 31)
UNIVERSE_CUTOFF = "2020-12-31"
EXPECTED_PER_DAY = 288
MIN_Q_DAYS = 30
GAP_H = 1
ASSET_MIN, QUARTER_MIN, MIN_ASSETS, BIAS_PP = 0.95, 0.90, 15, 15.0
HERE = Path(__file__).resolve().parent


def fetch(url, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 451):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


def s3_list(prefix, fetcher=fetch):
    """→ [(key, last_modified_iso)] celého prefixu."""
    out, marker = [], ""
    while True:
        q = {"prefix": prefix}
        if marker:
            q["marker"] = marker
        root = ET.fromstring(fetcher(f"{S3}?{urllib.parse.urlencode(q)}"))
        page = [(c.findtext(f"{NS}Key"), c.findtext(f"{NS}LastModified")) for c in root.findall(f"{NS}Contents")]
        out += page
        if root.findtext(f"{NS}IsTruncated") != "true" or not page:
            return out
        marker = root.findtext(f"{NS}NextMarker") or page[-1][0]


def universe(path):
    rows = list(csv.DictReader(open(path)))
    out = []
    for r in rows:
        if r["first_day"] > UNIVERSE_CUTOFF:
            continue
        first = dt.date.fromisoformat(r["first_day"])
        last = dt.date.fromisoformat(r["last_bar_day"]) - dt.timedelta(days=int(r["zero_volume_tail_days"] or 0))
        start, end = max(first, WIN_FROM), min(last, WIN_TO)
        out.append({"symbol": r["symbol"], "delisted": r["status"] != "active", "start": start, "end": end,
                    "in_window": start <= end})
    return out


DAY_RE = re.compile(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip$")


def file_day(key):
    """→ den souboru, nebo None pro nestandardní název (dodatek 1: počítá se, nezahrnuje)."""
    m = DAY_RE.search(key)
    return dt.date.fromisoformat(m.group(1)) if m else None


def parse_points(payload, day):
    """→ (set platných 5min indexů 0..287, počet neplatných řádků)."""
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    good, bad = set(), 0
    for r in csv.reader(io.StringIO(text)):
        if not r or not r[0][:1].isdigit():
            continue  # hlavička
        try:
            t = dt.datetime.fromisoformat(r[0].strip())
            oi = float(r[2])
        except (ValueError, IndexError):
            bad += 1
            continue
        if t.date() != day or t.second or t.minute % 5 or not (oi > 0):
            bad += 1
            continue
        good.add((t.hour * 60 + t.minute) // 5)
    return good, bad


def get_verified(key, cache, fetcher=fetch):
    url = f"{VISION}/{key}"
    p = Path(cache) / key
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
            ck = cp.read_bytes()
        else:
            ck = fetcher(url + ".CHECKSUM")
            cp.write_bytes(ck)
        status = "ok" if ck.decode().split()[0].lower() == sha else "MISMATCH"
    except urllib.error.HTTPError:
        status = "missing"
    return payload, sha, status


def quarter(d):
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def gaps(slots_by_day, start, end):
    """Výpadky ≥ GAP_H h na souvislé 5min ose živého období → (počet, nejdelší h, celkem h)."""
    n = longest = total = run = 0
    d = start
    while d <= end:
        s = slots_by_day.get(d, set())
        for i in range(EXPECTED_PER_DAY):
            if i in s:
                if run >= GAP_H * 12:
                    n += 1
                    longest = max(longest, run)
                    total += run
                run = 0
            else:
                run += 1
        d += dt.timedelta(days=1)
    if run >= GAP_H * 12:
        n += 1
        longest = max(longest, run)
        total += run
    return n, round(longest / 12, 2), round(total / 12, 2)


def audit_symbol(u, listing, cache, fetcher=fetch):
    sym, start, end = u["symbol"], u["start"], u["end"]
    zips = [(k, lm) for k, lm in listing if k.endswith(".zip")]
    files = {file_day(k): (k, lm) for k, lm in zips if file_day(k)}
    odd_keys = [k for k, _ in zips if not file_day(k)]
    manifest, slots, bad_rows, delays = [], {}, 0, []
    for day in sorted(files):
        if not (start <= day <= end):
            continue
        key, lm = files[day]
        try:
            payload, sha, st = get_verified(key, cache, fetcher)
        except urllib.error.HTTPError as e:
            manifest.append({"key": key, "last_modified": lm, "sha256": None, "checksum": f"http_{e.code}"})
            continue
        manifest.append({"key": key, "last_modified": lm, "sha256": sha, "checksum": st})
        if lm:
            avail = dt.datetime.fromisoformat(lm.replace("Z", "+00:00"))
            ev = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
            delays.append((day, (avail - ev).total_seconds() / 3600))
        if st != "ok":
            continue  # neshoda/chybějící checksum = soubor se nepočítá
        good, bad = parse_points(payload, day)
        slots[day] = good
        bad_rows += bad
    q_exp, q_got = defaultdict(int), defaultdict(int)
    d = start
    while d <= end:
        q_exp[quarter(d)] += EXPECTED_PER_DAY
        q_got[quarter(d)] += len(slots.get(d, ()))
        d += dt.timedelta(days=1)
    exp = sum(q_exp.values())
    got = sum(q_got.values())
    ng, longest, total_h = gaps(slots, start, end)
    qrows = [{"symbol": sym, "quarter": q, "live_days": q_exp[q] // EXPECTED_PER_DAY, "expected": q_exp[q],
              "valid": q_got[q], "coverage": round(q_got[q] / q_exp[q], 6),
              "evaluated": q_exp[q] // EXPECTED_PER_DAY >= MIN_Q_DAYS} for q in sorted(q_exp)]
    arow = {"symbol": sym, "delisted": u["delisted"], "start": str(start), "end": str(end),
            "live_days": exp // EXPECTED_PER_DAY, "files_listed": sum(start <= x <= end for x in files),
            "files_ok": len(slots), "checksum_bad": sum(m["checksum"] != "ok" for m in manifest),
            "expected": exp, "valid": got, "coverage": round(got / exp, 6) if exp else 0.0,
            "invalid_rows": bad_rows, "gaps_ge1h": ng, "longest_gap_h": longest, "gap_hours_total": total_h,
            "first_metrics_day": str(min(files)) if files else "", "nonstandard_keys": len(odd_keys),
            "worst_quarter_cov": min((r["coverage"] for r in qrows if r["evaluated"]), default=None)}
    return arow, qrows, manifest, delays


def gate(arows, qrows):
    inw = [a for a in arows if a["live_days"] > 0]
    passing = [a for a in inw if a["coverage"] >= ASSET_MIN and
               (a["worst_quarter_cov"] is None or a["worst_quarter_cov"] >= QUARTER_MIN)]
    by_q = defaultdict(int)
    allq = set()
    for r in qrows:
        allq.add(r["quarter"])
        if r["coverage"] >= QUARTER_MIN and r["evaluated"]:
            by_q[r["quarter"]] += 1
    quarters = [q for q in sorted(allq) if "2022Q1" <= q <= "2026Q3"]
    worst_q = min(quarters, key=lambda q: by_q[q]) if quarters else None
    share_all = 100 * sum(a["delisted"] for a in inw) / len(inw) if inw else 0.0
    share_pass = 100 * sum(a["delisted"] for a in passing) / len(passing) if passing else 0.0
    g1 = len(passing) >= MIN_ASSETS
    g2 = bool(quarters) and all(by_q[q] >= MIN_ASSETS for q in quarters)
    g3 = abs(share_pass - share_all) <= BIAS_PP
    return {"assets_in_window": len(inw), "assets_passing": len(passing),
            "passing_symbols": sorted(a["symbol"] for a in passing),
            "assets_per_quarter_ge90": {q: by_q[q] for q in quarters},
            "worst_quarter": worst_q, "worst_quarter_assets": by_q[worst_q] if worst_q else 0,
            "delisted_share_universe_pct": round(share_all, 2), "delisted_share_passing_pct": round(share_pass, 2),
            "G1_min_assets": g1, "G2_every_quarter": g2, "G3_selection_bias": g3,
            "verdict": "GO (jen návrh protokolu A3, denní dostupnost)" if (g1 and g2 and g3) else "NO-GO"}


def delay_stats(delays):
    by_y = defaultdict(list)
    for d, h in delays:
        by_y[d.year].append(h)
    out = []
    for y, hs in sorted(by_y.items()):
        hs.sort()
        pick = lambda p: round(hs[min(len(hs) - 1, int(p * len(hs)))], 2)
        out.append({"year": y, "n": len(hs), "min_h": round(hs[0], 2), "median_h": pick(0.5), "p90_h": pick(0.9),
                    "p99_h": pick(0.99), "max_h": round(hs[-1], 2), "share_le_1h": round(sum(h <= 1 for h in hs) / len(hs), 4)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/vision-metrics")
    ap.add_argument("--outdir", default=str(HERE))
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.outdir)
    uni = universe(HERE / "listings_frozen.csv")
    print(f"universe {len(uni)} symbols, in window {sum(u['in_window'] for u in uni)}", flush=True)
    arows, qrows, manifest, delays = [], [], [], []

    def one(u):
        if not u["in_window"]:
            return {"symbol": u["symbol"], "delisted": u["delisted"], "start": str(u["start"]), "end": str(u["end"]),
                    "live_days": 0, "coverage": 0.0, "worst_quarter_cov": None, "note": "mimo okno"}, [], [], []
        try:
            listing = s3_list(f"data/futures/um/daily/metrics/{u['symbol']}/")
            return audit_symbol(u, listing, a.cache)
        except Exception as e:  # dodatek 1: chyba aktiva = pokrytí 0 (konzervativně), běh pokračuje
            return {"symbol": u["symbol"], "delisted": u["delisted"], "start": str(u["start"]), "end": str(u["end"]),
                    "live_days": (u["end"] - u["start"]).days + 1, "expected": 288 * ((u["end"] - u["start"]).days + 1),
                    "valid": 0, "coverage": 0.0, "worst_quarter_cov": 0.0, "note": f"chyba: {type(e).__name__}: {e}"[:200]}, [], [], []

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, (ar, qr, mf, dl) in enumerate(ex.map(one, uni), 1):
            arows.append(ar), qrows.extend(qr), manifest.extend(mf), delays.extend(dl)
            print(f"[{i}/{len(uni)}] {ar['symbol']} cov={ar['coverage']:.4f} worstQ={ar.get('worst_quarter_cov')}", flush=True)
    g = gate(arows, qrows)
    ds = delay_stats(delays)
    afields = ["symbol", "delisted", "start", "end", "live_days", "files_listed", "files_ok", "checksum_bad", "expected",
               "valid", "coverage", "worst_quarter_cov", "invalid_rows", "gaps_ge1h", "longest_gap_h", "gap_hours_total",
               "first_metrics_day", "nonstandard_keys", "note"]
    with open(out / "coverage_assets.csv", "w", newline="") as f:
        w = csv.DictWriter(f, afields, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(arows, key=lambda r: r["symbol"]))
    with open(out / "coverage_quarters.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["symbol", "quarter", "live_days", "expected", "valid", "coverage", "evaluated"])
        w.writeheader()
        w.writerows(qrows)
    with open(out / "publication_delay.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(ds[0].keys()) if ds else ["year"])
        w.writeheader()
        w.writerows(ds)
    with gzip.open(out / "data_source.json.gz", "wt") as f:
        json.dump(manifest, f)
    inw = [r for r in arows if r["live_days"] > 0]
    worst = min(inw, key=lambda r: r["coverage"]) if inw else None
    res = {"protocol": "PROTOCOL.md", "window": [str(WIN_FROM), str(WIN_TO)], "gate": g,
           "worst_asset": {k: worst[k] for k in ("symbol", "coverage", "delisted")} if worst else None,
           "files": len(manifest), "checksum_not_ok": sum(m["checksum"] != "ok" for m in manifest),
           "publication_delay": ds,
           "missing_last_modified": sum(1 for m in manifest if not m["last_modified"])}
    (out / "audit.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
