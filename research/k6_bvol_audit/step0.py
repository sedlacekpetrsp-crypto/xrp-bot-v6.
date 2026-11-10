"""K6 krok 0: datový audit Binance Vision BVOLIndex. Viz PROTOCOL.md. PAPER, veřejná data, bez secrets, bez výnosů.

  python -m research.k6_bvol_audit.step0 run --outdir research/k6_bvol_audit
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
PREFIX = "data/option/daily/BVOLIndex/"
EOH_PREFIX = "data/option/daily/EOHSummary/"
ALLOWED_CADENCE = (1, 60, 300, 3600)
MIN_DAYS, MIN_RUN_COV, MIN_Q_COV, MAX_LAG_D, MAX_STALE_D = 548, 0.95, 0.90, 3, 7
DAY_S = 86400


def http(url: str, tries: int = 4) -> tuple[int, bytes]:
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "k6-audit"}), timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return e.code, e.read()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2 * (i + 1))
    return 0, b""


def _tag(xml: str, name: str) -> list[str]:
    return re.findall(rf"<{name}>(.*?)</{name}>", xml, re.S)


def s3_list(prefix: str, delimiter: str = "") -> tuple[list[dict], list[str]]:
    objs, prefixes, marker = [], [], ""
    while True:
        q = {"prefix": prefix, "marker": marker}
        if delimiter:
            q["delimiter"] = delimiter
        code, body = http(S3 + "?" + urllib.parse.urlencode(q))
        if code != 200:
            raise RuntimeError(f"S3 list {prefix} -> {code}")
        xml = body.decode()
        for blk in _tag(xml, "Contents"):
            objs.append({"key": _tag(blk, "Key")[0], "last_modified": _tag(blk, "LastModified")[0],
                         "size": int(_tag(blk, "Size")[0])})
        prefixes += [_tag(p, "Prefix")[0] for p in _tag(xml, "CommonPrefixes")]
        if _tag(xml, "IsTruncated")[:1] != ["true"]:
            return objs, prefixes
        nm = _tag(xml, "NextMarker")
        marker = nm[0] if nm else (objs[-1]["key"] if objs else prefixes[-1])


def file_date(key: str) -> dt.date | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", key)
    return dt.date.fromisoformat(m.group(1)) if m else None


def lag_days(last_modified: str, d: dt.date) -> float:
    lm = dt.datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
    ref = dt.datetime.combine(d + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
    return (lm - ref).total_seconds() / DAY_S


def parse_csv(raw: bytes) -> tuple[list[str], list[int], list[float]]:
    """Vrací (hlavička, calc_time ms, hodnoty). Časový sloupec = 'calc_time' nebo první int > 1e12."""
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8", "replace"))))
    header: list[str] = []
    if rows and not re.fullmatch(r"\d+", rows[0][0].strip()):
        header, rows = [c.strip() for c in rows[0]], rows[1:]
    if not rows:
        return header, [], []
    ti = header.index("calc_time") if "calc_time" in header else next(
        i for i, c in enumerate(rows[0]) if re.fullmatch(r"\d{12,}", c.strip()))
    vi = header.index("index_value") if "index_value" in header else len(rows[0]) - 1
    ts, vals = [], []
    for r in rows:
        try:
            ts.append(int(float(r[ti])))
            vals.append(float(r[vi]))
        except (ValueError, IndexError):
            continue
    return header, ts, vals


def diff_counter(ts: list[int]) -> Counter:
    s = sorted(set(ts))
    return Counter(round((b - a) / 1000) for a, b in zip(s, s[1:]))


def cadence(diffs: Counter) -> int:
    return diffs.most_common(1)[0][0] if diffs else 0


def gate(days: list[dict], cad: int, audit_day: dt.date) -> dict:
    """days: seřazené {date, ok(file+checksum+pit), points, outside}. Vrací nejdelší platný běh a verdikt."""
    exp = DAY_S // cad if cad in ALLOWED_CADENCE else 0
    runs, cur = [], []
    by = {d["date"]: d for d in days}
    if days:
        x, d1 = days[0]["date"], days[-1]["date"]
        while x <= d1:
            r = by.get(x)
            if r and r["ok"]:
                cur.append(r)
            elif cur:
                runs.append(cur)
                cur = []
            x += dt.timedelta(days=1)
        if cur:
            runs.append(cur)
    fresh_runs = [r for r in runs if (audit_day - r[-1]["date"]).days <= MAX_STALE_D]
    best = max(fresh_runs or runs, key=len, default=[])
    res = {"cadence_s": cad, "cadence_allowed": cad in ALLOWED_CADENCE, "run_days": len(best),
           "run_start": str(best[0]["date"]) if best else None, "run_end": str(best[-1]["date"]) if best else None}
    if not best or not exp:
        return {**res, "run_cov": 0.0, "min_quarter_cov": 0.0, "outside_rows": 0, "days_below_95": 0, "GO": False}
    cov = sum(min(r["points"], exp) for r in best) / (exp * len(best))
    q: dict[str, list[int]] = {}
    for r in best:
        k = f"{r['date'].year}Q{(r['date'].month - 1) // 3 + 1}"
        q.setdefault(k, []).append(min(r["points"], exp))
    qcov = {k: sum(v) / (exp * len(v)) for k, v in q.items()}
    outside = sum(r["outside"] for r in best)
    fresh = (audit_day - best[-1]["date"]).days <= MAX_STALE_D
    go = (len(best) >= MIN_DAYS and cov >= MIN_RUN_COV and min(qcov.values()) >= MIN_Q_COV
          and outside == 0 and fresh)
    return {**res, "run_cov": round(cov, 5), "quarter_cov": {k: round(v, 4) for k, v in qcov.items()},
            "min_quarter_cov": round(min(qcov.values()), 5), "outside_rows": outside, "fresh": fresh,
            "days_below_95": sum(1 for r in best if r["points"] < 0.95 * exp), "GO": go}


def audit_file(obj: dict, chk_keys: set[str]) -> dict:
    d = file_date(obj["key"])
    out = {"key": obj["key"], "date": d, "last_modified": obj["last_modified"], "lag_days": round(lag_days(obj["last_modified"], d), 3)}
    code, raw = http(DL + obj["key"])
    out["sha256"] = hashlib.sha256(raw).hexdigest() if code == 200 else ""
    exp = ""
    if obj["key"] + ".CHECKSUM" in chk_keys:
        c2, b2 = http(DL + obj["key"] + ".CHECKSUM")
        exp = b2.decode().split()[0] if c2 == 200 and b2 else ""
    out["checksum_ok"] = bool(out["sha256"]) and exp == out["sha256"]
    header, ts, vals = [], [], []
    if code == 200:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            header, ts, vals = parse_csv(z.read(z.namelist()[0]))
    lo = int(dt.datetime.combine(d, dt.time(), dt.timezone.utc).timestamp() * 1000)
    uniq = sorted(set(ts))
    out.update(header="|".join(header), rows=len(ts), points=sum(1 for t in uniq if lo <= t < lo + DAY_S * 1000),
               outside=sum(1 for t in uniq if not lo <= t < lo + DAY_S * 1000), dups=len(ts) - len(uniq),
               vmin=min(vals) if vals else None, vmax=max(vals) if vals else None,
               v_bad=sum(1 for v in vals if not 0 < v < 500), diffs=diff_counter(uniq),
               t_first=uniq[0] if uniq else None, t_last=uniq[-1] if uniq else None)
    return out


def run(outdir: str) -> dict:
    audit_day = dt.datetime.now(dt.timezone.utc).date()
    _, tickers = s3_list(PREFIX, "/")
    vcode, vbody = http(S3 + "?versions&" + urllib.parse.urlencode({"prefix": PREFIX, "max-keys": "5"}))
    eoh, _ = s3_list(EOH_PREFIX)
    summary = {"audit_day": str(audit_day), "tickers": tickers, "versions_api_http": vcode,
               "versions_api_snippet": vbody[:160].decode("utf-8", "replace"), "eoh_files": len(eoh), "per_ticker": {}}
    files_rows = []
    for tp in tickers:
        objs, _ = s3_list(tp)
        chk = {o["key"] for o in objs if o["key"].endswith(".CHECKSUM")}
        zips = [o for o in objs if o["key"].endswith(".zip") and file_date(o["key"])]
        with ThreadPoolExecutor(8) as ex:
            res = sorted(ex.map(lambda o: audit_file(o, chk), zips), key=lambda r: r["date"])
        diffs = Counter()
        for r in res:
            diffs.update(r["diffs"])
        ends = [(r["t_first"], r["t_last"]) for r in res if r["t_first"] is not None]
        diffs.update(round((b[0] - a[1]) / 1000) for a, b in zip(ends, ends[1:]))
        cad = cadence(diffs)
        max_gap = max(diffs, default=0)
        days = [{"date": r["date"], "points": r["points"], "outside": r["outside"],
                 "ok": r["checksum_ok"] and r["lag_days"] <= MAX_LAG_D} for r in res]
        g = gate(days, cad, audit_day)
        lags = sorted(r["lag_days"] for r in res)
        summary["per_ticker"][tp.rstrip("/").split("/")[-1]] = {
            **g, "files": len(res), "first_file": str(res[0]["date"]) if res else None,
            "last_file": str(res[-1]["date"]) if res else None, "checksum_fail": sum(not r["checksum_ok"] for r in res),
            "not_pit": sum(r["lag_days"] > MAX_LAG_D for r in res), "lag_p50": lags[len(lags) // 2] if lags else None,
            "lag_max": lags[-1] if lags else None, "max_gap_s": max_gap, "headers": sorted({r["header"] for r in res}),
            "v_min": min((r["vmin"] for r in res if r["vmin"] is not None), default=None),
            "v_max": max((r["vmax"] for r in res if r["vmax"] is not None), default=None),
            "v_bad": sum(r["v_bad"] for r in res), "dups": sum(r["dups"] for r in res),
            "diff_top": diffs.most_common(5)}
        files_rows += [{k: r[k] for k in ("key", "date", "last_modified", "lag_days", "sha256", "checksum_ok", "rows",
                                           "points", "outside", "dups")} for r in res]
    pt = summary["per_ticker"]
    need = [k for k in pt if k.startswith(("BTC", "ETH"))]
    summary["GO"] = bool(need) and {k[:3] for k in need} >= {"BTC", "ETH"} and all(pt[k]["GO"] for k in need)
    summary["verdict"] = "GO (jen návrh výkonnostního protokolu)" if summary["GO"] else "DATA NO-GO"
    with open(f"{outdir}/step0_files.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(files_rows[0]) if files_rows else ["key"])
        w.writeheader()
        w.writerows(files_rows)
    with open(f"{outdir}/step0_summary.json", "w") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False, default=str)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--outdir", default="research/k6_bvol_audit")
    a = ap.parse_args()
    s = run(a.outdir)
    print(json.dumps({k: v for k, v in s.items() if k != "per_ticker"}, ensure_ascii=False, default=str))
    for k, v in s["per_ticker"].items():
        print(k, json.dumps({x: v[x] for x in v if x != "quarter_cov"}, ensure_ascii=False, default=str))
