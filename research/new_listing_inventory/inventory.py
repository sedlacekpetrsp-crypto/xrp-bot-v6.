"""A1 krok 1 — PIT inventura listingů/delistingů USDT-M perpů (PROTOCOL.md). Bez výkonnosti.

    python -m research.new_listing_inventory.inventory --cache /tmp/vision-inv --outdir research/new_listing_inventory

Jen veřejná data Binance Vision (+ best-effort veřejné exchangeInfo). Žádné klíče, žádné objednávky.
Výstup neobsahuje ceny ani výnosy.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION = "https://data.binance.vision"
EXINFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"
END_DAY = dt.date(2026, 10, 31)
FIRST_MONTH = (2019, 9)
LAST_MONTH = (2026, 10)
ELIG_FROM, ELIG_TO = dt.date(2020, 1, 1), dt.date(2026, 4, 30)
WINDOW = 180
GAP_SEGMENT_DAYS = 30
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-research/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 451):
                raise
            last = e
        except Exception as e:  # síťové chyby: opakovat
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


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


def is_usdt_perp(sym):
    return sym.endswith("USDT") and "_" not in sym


def ms_to_dt(ms):
    ms = ms // 1000 if ms > 10 ** 14 else ms
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


def csv_rows(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().isdigit()]


def kline_days(payload):
    return sorted({ms_to_dt(int(r[0])).date() for r in csv_rows(payload)})


def month_tag(key):
    """…/BTCUSDT-1d-2021-03.zip → (2021, 3)"""
    stem = key.rsplit("/", 1)[1].split(".")[0]
    y, m = stem.split("-")[-2:]
    return int(y), int(m)


def in_range(ym):
    return FIRST_MONTH <= ym <= LAST_MONTH


def get_verified(url, cache, fetcher=fetch):
    """Stáhne archiv + .CHECKSUM; → (payload, sha256, checksum_status)."""
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


def segments(days):
    if not days:
        return 0
    n = 1
    for a, b in zip(days, days[1:]):
        if (b - a).days > GAP_SEGMENT_DAYS:
            n += 1
    return n


def analyse_symbol(sym, kline_keys, funding_keys, cache, fetcher=fetch):
    """Čistá funkce nad seznamy klíčů + stažením; vrací (řádek, manifest)."""
    months = sorted(month_tag(k) for k in kline_keys if k.endswith(".zip") and in_range(month_tag(k)))
    fmonths = sorted({month_tag(k) for k in funding_keys if k.endswith(".zip") and in_range(month_tag(k))})
    manifest, days = [], set()
    for ym in months:
        url = f"{VISION}/data/futures/um/monthly/klines/{sym}/1d/{sym}-1d-{ym[0]}-{ym[1]:02d}.zip"
        payload, sha, st = get_verified(url, cache, fetcher)
        manifest.append({"url": url, "sha256": sha, "checksum": st})
        days.update(d for d in kline_days(payload) if d <= END_DAY)
    days = sorted(days)
    row = {"symbol": sym, "kline_months": len(months), "funding_months": len(fmonths)}
    if not days:
        row.update(first_day="", last_day="", n_days=0, status="no_data")
        return row, manifest
    first, last = days[0], days[-1]
    first_trade, source = dt.datetime.combine(first, dt.time(), dt.timezone.utc), "1d_open_fallback"
    url = f"{VISION}/data/futures/um/daily/klines/{sym}/1m/{sym}-1m-{first.isoformat()}.zip"
    try:
        payload, sha, st = get_verified(url, cache, fetcher)
        manifest.append({"url": url, "sha256": sha, "checksum": st})
        rows = csv_rows(payload)
        if rows:
            first_trade, source = min(ms_to_dt(int(r[0])) for r in rows), "1m_first_bar"
    except urllib.error.HTTPError:
        pass
    span = [first + dt.timedelta(d) for d in range((last - first).days + 1)]
    dayset = set(days)
    missing = [d for d in span if d not in dayset]
    first180_end = first + dt.timedelta(WINDOW)
    kmonths = {(d.year, d.month) for d in days}
    row.update(
        first_trade_utc=first_trade.isoformat(), first_trade_source=source,
        first_day=first.isoformat(), last_day=last.isoformat(),
        status="active" if last == END_DAY else "delisted_or_halted",
        n_days=len(days), missing_days=len(missing),
        missing_days_first180=sum(1 for d in missing if d < first180_end),
        gap_segments=segments(days), reused_ticker=segments(days) > 1,
        funding_ok=bool(fmonths) and kmonths <= set(fmonths),
    )
    return row, manifest


def apply_exchangeinfo(row, info):
    s = info.get(row["symbol"]) if info is not None else None
    row["onboard_date_utc"] = ms_to_dt(s["onboardDate"]).isoformat() if s and s.get("onboardDate") else ""
    row["exchangeinfo_status"] = (s or {}).get("status", "absent" if info is not None else "unavailable")
    if row.get("status") == "delisted_or_halted" and info is not None:
        row["status"] = "delisted" if (not s or s.get("status") in ("SETTLING", "CLOSE")) else "halted_unconfirmed"
    return row


def eligibility(row):
    if row.get("status") == "no_data":
        return False, "no_data"
    first = dt.date.fromisoformat(row["first_day"])
    last = dt.date.fromisoformat(row["last_day"])
    if not (ELIG_FROM <= first <= ELIG_TO):
        return False, "listing_outside_2020-01..2026-04"
    if row["reused_ticker"]:
        return False, "reused_ticker"
    if not row["funding_ok"]:
        return False, "funding_incomplete"
    if row["missing_days_first180"] > 2:
        return False, "missing_days_first180>2"
    if (last - first).days + 1 < WINDOW and row["status"] == "active":
        return False, "short_history"
    return True, ""


def gates(rows, checksum_counts):
    el = [r for r in rows if r["eligible_a1"]]
    delisted = [r for r in el if r["status"] in ("delisted", "delisted_or_halted", "halted_unconfirmed")]
    by_year = {}
    for r in el:
        by_year[r["first_day"][:4]] = by_year.get(r["first_day"][:4], 0) + 1
    with_ob = [r for r in rows if r.get("onboard_date_utc") and r.get("first_trade_utc")]
    match = sum(1 for r in with_ob if abs((dt.datetime.fromisoformat(r["first_trade_utc"]) - dt.datetime.fromisoformat(r["onboard_date_utc"])).total_seconds()) <= 86400)
    g = {
        "G1_eligible_ge_100": {"value": len(el), "pass": len(el) >= 100},
        "G2_delisted_eligible_ge_10": {"value": len(delisted), "pass": len(delisted) >= 10},
        "G3_each_year_2021_2025_ge_10": {"value": {y: by_year.get(str(y), 0) for y in range(2021, 2026)},
                                         "pass": all(by_year.get(str(y), 0) >= 10 for y in range(2021, 2026))},
        "G4_onboard_match_ge_90pct": {"value": f"{match}/{len(with_ob)}",
                                      "pass": (match / len(with_ob) >= 0.9) if with_ob else None},
        "G5_checksums_ok": {"value": checksum_counts, "pass": checksum_counts.get("MISMATCH", 0) == 0},
    }
    g["GO"] = all(g[k]["pass"] for k in ("G1_eligible_ge_100", "G2_delisted_eligible_ge_10", "G3_each_year_2021_2025_ge_10", "G5_checksums_ok"))
    return g, by_year


COLS = ["symbol", "first_trade_utc", "first_trade_source", "first_day", "last_day", "status", "n_days", "missing_days",
        "missing_days_first180", "gap_segments", "reused_ticker", "kline_months", "funding_months", "funding_ok",
        "onboard_date_utc", "exchangeinfo_status", "eligible_a1", "ineligible_reason"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.outdir)
    t0 = time.time()
    pm, _ = s3_list("data/futures/um/monthly/klines/")
    pd, _ = s3_list("data/futures/um/daily/klines/")
    all_syms = sorted({p.rstrip("/").rsplit("/", 1)[1] for p in pm + pd})
    syms = [s for s in all_syms if is_usdt_perp(s)]
    daily_only = sorted({p.rstrip("/").rsplit("/", 1)[1] for p in pd} - {p.rstrip("/").rsplit("/", 1)[1] for p in pm})
    print(f"symbols total {len(all_syms)}, USDT perps {len(syms)}, daily-only {len(daily_only)}", flush=True)
    try:
        info = {s["symbol"]: s for s in json.loads(fetch(EXINFO))["symbols"]}
        info_note = f"ok ({len(info)} symbols)"
    except Exception as e:  # best effort
        info, info_note = None, f"unavailable: {type(e).__name__} {getattr(e, 'code', '')}".strip()
    print("exchangeInfo", info_note, flush=True)

    def work(sym):
        _, kk = s3_list(f"data/futures/um/monthly/klines/{sym}/1d/")
        _, fk = s3_list(f"data/futures/um/monthly/fundingRate/{sym}/")
        return analyse_symbol(sym, kk, fk, a.cache)

    rows, manifest = [], []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, (row, man) in enumerate(ex.map(work, syms), 1):
            rows.append(row)
            manifest += man
            if i % 50 == 0:
                print(f"{i}/{len(syms)} {time.time() - t0:.0f}s", flush=True)
    for r in rows:
        apply_exchangeinfo(r, info)
        r["eligible_a1"], r["ineligible_reason"] = eligibility(r)
    cs = {}
    for m in manifest:
        cs[m["checksum"]] = cs.get(m["checksum"], 0) + 1
    g, by_year = gates(rows, cs)
    status_counts = {}
    for r in rows:
        status_counts[r.get("status")] = status_counts.get(r.get("status"), 0) + 1
    reasons = {}
    for r in rows:
        if not r["eligible_a1"]:
            reasons[r["ineligible_reason"]] = reasons.get(r["ineligible_reason"], 0) + 1
    summary = {
        "protocol": "research/new_listing_inventory/PROTOCOL.md", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "symbols_in_archive": len(all_syms), "usdt_perps": len(syms), "daily_only_symbols": daily_only,
        "exchangeinfo": info_note, "status_counts": status_counts, "eligible_by_listing_year": by_year,
        "ineligible_reasons": reasons, "gates": g, "archives": len(manifest), "checksums": cs,
        "runtime_s": round(time.time() - t0),
    }
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "listings.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r.get("first_day") or "9", r["symbol"])):
            w.writerow({c: r.get(c, "") for c in COLS})
    (out / "data_source.json").write_text(json.dumps({"source": VISION, "listing": S3, "archives": manifest}, indent=1))
    (out / "inventory.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print("INVENTORY_SUMMARY " + json.dumps({k: summary[k] for k in ("usdt_perps", "status_counts", "eligible_by_listing_year", "checksums", "exchangeinfo")}
                                            | {"gates": {k: (v["pass"] if isinstance(v, dict) else v) for k, v in g.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
