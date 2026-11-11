"""K7 krok 0: PIT audit kalendáře FOMC + pokrytí BTC 1h. Viz PROTOCOL.md (dodatek 1). PAPER, veřejná data, bez výnosů.

  python -m research.k7_macro_calendar.step0 run --outdir research/k7_macro_calendar
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html as htmllib
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
CAL = "www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
STMT = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{d}a.htm"
CDX = "https://web.archive.org/cdx/search/cdx?url={u}&from={a}&to={b}&filter=statuscode:200&output=json"
SNAP = "https://web.archive.org/web/{ts}id_/https://{u}"
BV = "https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{ym}.zip"
YEARS = range(2018, 2027)
MIN_EVENTS, MIN_FINAL, MIN_LEAD_D, WIN_H = 60, 15, 7, 48
MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9
MRE = "|".join(sorted(MONTHS, key=len, reverse=True))
BAD_TAG = re.compile(r"unscheduled|notation|conference call|cancel", re.I)


def http(url: str, tries: int = 4) -> tuple[int, bytes]:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (k7-pit-audit; research)"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return e.code, b""
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3 * (i + 1))
    return 0, b""


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"[ \t\r\f\v]+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "\n", h)))


def year_sections(html: str) -> dict[int, str]:
    """Rozdělí stránku podle nadpisů '<YYYY> FOMC Meetings' (HTML zachováno)."""
    hs = list(re.finditer(r"(\d{4})\s+FOMC\s+Meetings", html))
    out: dict[int, str] = {}
    for i, m in enumerate(hs):
        end = hs[i + 1].start() if i + 1 < len(hs) else len(html)
        out.setdefault(int(m.group(1)), html[m.end():end])
    return out


def _mk(year: int, m1: str, m2: str | None, d1: str, d2: str | None, tag: str) -> dict | None:
    day = int(d2 or d1)
    span = bool(m2 and d2 and int(d2) < int(d1))  # např. Oct/Nov 31-1 ⇒ konec v druhém měsíci
    mm = MONTHS.get((m2 if span else m1).lower().rstrip("."))
    if not mm:
        return None
    try:
        end = dt.date(year, mm, day)
    except ValueError:
        return None
    return {"end_date": end, "tag": tag.strip(), "raw": f"{m1}{'/' + m2 if m2 else ''} {d1}{'-' + d2 if d2 else ''} {tag}".strip()}


def parse_meetings(section_html: str, year: int) -> tuple[list[dict], str]:
    """Vrací (schůze, metoda). 1) strukturované divy fomc-meeting__month/date, 2) záložní textový regex."""
    out = []
    for mo, da in re.findall(r'fomc-meeting__month[^>]*>(.*?)</div>.*?fomc-meeting__date[^>]*>(.*?)</div>',
                             section_html, re.S):
        mt, dtxt = _text(mo).strip(), _text(da).strip()
        mm = re.search(rf"\b({MRE})\.?(?:\s*/\s*({MRE}))?", mt, re.I)
        dd = re.search(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s*\*?\s*(\([^)]*\))?", dtxt)
        if mm and dd:
            e = _mk(year, mm.group(1), mm.group(2), dd.group(1), dd.group(2), (dd.group(3) or "") + " " + dtxt[dd.end():])
            if e:
                out.append(e)
    if out:
        return out, "structured"
    txt = _text(section_html)
    pat = re.compile(rf"(?<![\w,])({MRE})\.?(?:\s*/\s*({MRE}))?\s+(\d{{1,2}})(?:\s*[-–]\s*(\d{{1,2}}))?\s*\*?"
                     rf"(?!\s*,\s*\d{{4}})\s*(\([^)]{{0,40}}\))?", re.I)
    for m in pat.finditer(txt):
        if re.search(r"released\s*$", txt[max(0, m.start() - 12):m.start()], re.I):
            continue
        e = _mk(year, m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or "")
        if e:
            out.append(e)
    return out, "text"


def scheduled(meetings: list[dict]) -> list[dict]:
    seen, out = set(), []
    for m in meetings:
        if BAD_TAG.search(m["tag"]) or m["end_date"] in seen:
            continue
        seen.add(m["end_date"])
        out.append(m)
    return sorted(out, key=lambda m: m["end_date"])


def announce_utc(d: dt.date) -> dt.datetime:
    return dt.datetime.combine(d, dt.time(14, 0), ET).astimezone(UTC)


def window_hours(t: dt.datetime) -> list[int]:
    t0 = int(t.timestamp()) // 3600 * 3600
    return [t0 + h * 3600 for h in range(-WIN_H, WIN_H)]


def coverage(hours_have: set[int], t: dt.datetime) -> float:
    need = window_hours(t)
    return sum(h in hours_have for h in need) / len(need)


def gate(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["pit_status"] == "PROVEN" and r["actual_at"] and r["coverage_1h"] >= 1.0]
    n = len(ok)
    final = n - (3 * n) // 4
    return {"eligible": n, "final_segment": final, "GO_counts": n >= MIN_EVENTS and final >= MIN_FINAL}


def klines_hours(raw_zip: bytes) -> set[int]:
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    out = set()
    for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())):
        if not r or not r[0].strip().isdigit():
            continue
        t = int(r[0])
        t = t // 1_000_000 if t > 10**14 else t // 1000
        out.add(t)
    return out


def run(outdir: str) -> dict:
    now = dt.datetime.now(UTC)
    snaps, rows, errors, notes = {}, [], [], []
    # 1) PIT snímky předem
    for y in YEARS:
        code, body = http(CDX.format(u=CAL, a=f"{y - 1}0701", b=f"{y - 1}1231235959"))
        caps = json.loads(body)[1:] if code == 200 and body.strip() else []
        info = {"year": y, "cdx_http": code, "captures": len(caps)}
        meets, method, ts = [], "", None
        for cap in reversed(caps):  # od nejnovějšího < Y-01-01
            ts = cap[1]
            c2, raw = http(SNAP.format(ts=ts, u=CAL))
            if c2 != 200 or not raw:
                continue
            sec = year_sections(raw.decode("utf-8", "replace")).get(y)
            if sec:
                meets, method = parse_meetings(sec, y)
            info.update(ts=ts, snap_sha256=sha(raw), method=method, parsed=len(meets),
                        url=SNAP.format(ts=ts, u=CAL))
            if meets:
                break
        info["scheduled"] = [str(m["end_date"]) for m in scheduled(meets)]
        info["excluded_tags"] = [m["raw"] for m in meets if BAD_TAG.search(m["tag"])]
        snaps[y] = info
        print(f"[snap] {y}: captures={len(caps)} ts={info.get('ts')} method={method} scheduled={len(info['scheduled'])}")
    # 2) realizace + 3) pokrytí
    hours: dict[str, set[int]] = {"BTCUSDT": set(), "ETHUSDT": set()}
    months: set[str] = set()
    events = []
    for y, info in snaps.items():
        ts = info.get("ts")
        fa = dt.datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=UTC) if ts and info["scheduled"] else None
        for ds in info["scheduled"]:
            d = dt.date.fromisoformat(ds)
            t = announce_utc(d)
            events.append((y, d, t, fa))
            for h in (t - dt.timedelta(hours=WIN_H), t + dt.timedelta(hours=WIN_H - 1)):
                months.add(h.strftime("%Y-%m"))
    files = []
    for s in hours:
        for ym in sorted(months):
            url = BV.format(s=s, ym=ym)
            c, raw = http(url)
            c2, ck = http(url + ".CHECKSUM")
            st = "missing"
            if c == 200 and raw:
                exp = ck.decode().split()[0] if c2 == 200 and ck else ""
                if exp and exp == sha(raw):
                    st = "ok"
                    hours[s] |= klines_hours(raw)
                else:
                    st = "checksum_error" if exp else "no_checksum"
                    errors.append(f"{s} {ym} {st}")
            files.append({"symbol": s, "month": ym, "http": c, "status": st})
    for y, d, t, fa in events:
        future = t + dt.timedelta(hours=WIN_H) > now
        c, raw = (0, b"") if future else http(STMT.format(d=d.strftime("%Y%m%d")))
        lead = (t - fa).total_seconds() / 86400 if fa else None
        pit = "PROVEN" if lead is not None and lead >= MIN_LEAD_D else "UNKNOWN"
        note = "future" if future else ("" if c == 200 else f"no_statement_http_{c} (zrušeno/přesunuto?)")
        rows.append({"event_id": f"FOMC-{d}", "source_url": snaps[y].get("url", ""),
                     "first_announced_at": fa.isoformat() if fa else "", "scheduled_at": t.isoformat(),
                     "actual_at": t.isoformat() if c == 200 else "", "evidence_hash": snaps[y].get("snap_sha256", ""),
                     "pit_status": pit, "coverage_1h": round(coverage(hours["BTCUSDT"], t), 4),
                     "actual_hash": sha(raw) if c == 200 else "", "eth_coverage_1h": round(coverage(hours["ETHUSDT"], t), 4),
                     "lead_days": round(lead, 1) if lead is not None else "", "note": note})
    g = gate(rows)
    verdict = "GO (jen data; výkon NESPOUŠTĚT)" if g["GO_counts"] and not errors else "DATA NO-GO"
    summ = {"audit_utc": now.isoformat(), "gate": g, "errors": errors, "verdict": verdict,
            "snapshots": snaps, "events_total": len(rows),
            "not_realized": [r["event_id"] for r in rows if not r["actual_at"] and r["note"] != "future"],
            "future": [r["event_id"] for r in rows if r["note"] == "future"],
            "pit_unknown": [r["event_id"] for r in rows if r["pit_status"] != "PROVEN"],
            "coverage_lt_1": [r["event_id"] for r in rows if r["coverage_1h"] < 1],
            "binance_files": {s: sum(f["status"] == "ok" for f in files if f["symbol"] == s) for s in hours},
            "notes": notes}
    with open(f"{outdir}/step0_events.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["event_id"])
        w.writeheader()
        w.writerows(rows)
    with open(f"{outdir}/step0_files.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "month", "http", "status"])
        w.writeheader()
        w.writerows(files)
    with open(f"{outdir}/step0_summary.json", "w") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: summ[k] for k in ("gate", "verdict", "events_total", "not_realized", "future",
                                           "pit_unknown", "coverage_lt_1", "binance_files", "errors")},
                     ensure_ascii=False, indent=1))
    return summ


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--outdir", default="research/k7_macro_calendar")
    a = ap.parse_args()
    run(a.outdir)


if __name__ == "__main__":
    main()
