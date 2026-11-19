"""K11 BINANCE_SPOT_DELIST_DRIFT — kolektor KROKU 0 (jen datový audit, žádné výnosy).

PROTOCOL.md §3 + dodatky 1–3. Výstup: ``events.csv`` + ``step0_manifest.json``; o verdiktu rozhoduje
``research.k11_step0_gate.audit_gate`` (beze změny) + kontrola úplnosti výčtu (dodatek 3).

Zásady:
- Z cen se nečte NIC: z Binance Vision klines se načítá jen sloupec ``open_time`` (existence minut).
- Síť jen přes injektovaný ``fetch(url) -> (status:int, body:bytes)``; běží výhradně v GitHub Actions.
- Fail closed: nejasný titulek, neplatný CHECKSUM, chybějící soubor ⇒ událost nezpůsobilá, nikdy imputace.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from research.k11_archive_pit_evidence import classify_archive_evidence
from research.k11_step0_gate import WINDOW_END, WINDOW_START, audit_gate

UTC = timezone.utc
LAG = timedelta(minutes=60)                  # PROTOCOL §3.3 L = 60 min
MIN_AFTER_ENTRY = timedelta(hours=24)        # perp se obchoduje ≥ 24 h po t_ann + L
COV_BEFORE, COV_AFTER = timedelta(days=7), timedelta(days=14)
MIN_MINUTE_COVERAGE = 0.95
PIT_FETCH_BEFORE = timedelta(days=7)         # dodatek 3: snímky stahované pro rozpor (viz PROTOCOL)
PIT_AFTER = timedelta(hours=24)
MAX_UNPARSED_SHARE = 0.05                    # dodatek 3: úplnost výčtu
PERP_PREFIXES = ("", "1000", "1000000", "1M")  # pevné pořadí aliasů, první s daty v den t_ann vyhrává

CMS_LIST = ("https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
            "?type=1&catalogId=161&pageNo={page}&pageSize=50")
CDX = ("https://web.archive.org/cdx/search/cdx?url={url}&matchType=prefix&output=json"
       "&fl=timestamp,original,statuscode,digest&from=20191201&to=20261108")
ARCHIVE_PREFIXES = (  # zmrazeno před daty (dodatek 2/3); žádná další zdrojová cesta po zhlédnutí dat
    "www.binance.com/en/support/announcement/c-161",
    "www.binance.com/en/support/announcement/delisting",
    "www.binance.com/bapi/composite/v1/public/cms/article/list/query",
)
VISION = "https://data.binance.vision/data/futures/um"

# ---------------------------------------------------------------- titulky (čisté funkce)
_SPOT_RE = re.compile(r"^\s*Binance\s+Will\s+Delist\s+(?P<body>.+)$", re.I)
_NOT_SPOT = re.compile(r"margin|futures|perpetual|contract|options|earn|loan|convert|savings|staking|"
                       r"trading\s+pairs?|monitoring|vote", re.I)
_TOKEN = re.compile(r"^[A-Z0-9]{2,15}$")


def classify_title(title: str) -> str:
    t = title or ""
    if re.search(r"monitoring\s+tag", t, re.I):
        return "monitoring_tag"
    if re.search(r"vote\s+to\s+delist", t, re.I):
        return "vote_to_delist"
    if re.search(r"margin", t, re.I):
        return "margin_delist"
    if re.search(r"futures|perpetual|contract", t, re.I):
        return "futures_delist"
    if re.search(r"removal\s+of\s+spot\s+trading\s+pairs|delist\s+.*trading\s+pairs?", t, re.I):
        return "pair_removal"
    m = _SPOT_RE.match(t)
    if m and not _NOT_SPOT.search(m.group("body")):
        return "spot_delist"
    return "other"


def parse_tokens(title: str):
    """Tokeny ze spotového titulku; None = nejednoznačné (fail closed, nikdy hádání)."""
    m = _SPOT_RE.match(title or "")
    if not m:
        return None
    body = re.split(r"\s+on\s+\d{4}-\d{2}-\d{2}|\s+on\s+[A-Z][a-z]+\s+\d", m.group("body"))[0]
    body = re.sub(r"\(([A-Z0-9]{2,15})\)", r" \1 ", body)       # „Bitcoin Standard (BTCST)“ ⇒ BTCST
    parts = [p.strip() for p in re.split(r",|&|\band\b", body) if p.strip()]
    out = []
    for p in parts:
        cands = [w for w in p.split() if _TOKEN.match(w)]
        if len(cands) != 1:
            return None
        out.append(cands[0])
    if not out or len(set(out)) != len(out):
        return None
    return out


# ---------------------------------------------------------------- Wayback (čisté funkce)
_CODE_URL = re.compile(r"/support/announcement/(?:detail/)?(?:[a-z0-9-]+-)?([0-9a-f]{32})")
_CODE_JSON = re.compile(r'"code"\s*:\s*"([0-9a-f]{32})"')


def extract_codes(body: bytes) -> set:
    """CMS `code` článků ve snímku (odkazy v HTML nebo pole `code` v archivované JSON odpovědi)."""
    text = body.decode("utf-8", "replace")
    return set(_CODE_URL.findall(text)) | set(_CODE_JSON.findall(text))


def parse_cdx(rows) -> list:
    """CDX JSON ⇒ [(capture_utc, original, digest)] jen pro status 200 (dodatek 2)."""
    if not rows:
        return []
    head, out = rows[0], []
    idx = {k: head.index(k) for k in ("timestamp", "original", "statuscode", "digest")}
    for r in rows[1:]:
        if r[idx["statuscode"]] != "200":
            continue
        ts = r[idx["timestamp"]]
        if not re.fullmatch(r"\d{14}", ts):
            raise ValueError("neplatný CDX timestamp")
        out.append((datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=UTC), r[idx["original"]],
                    r[idx["digest"]]))
    return sorted(set(out))


def needed_captures(captures, releases):
    """Snímky v sjednocení oken [release − 7 d, release + 24 h] (dodatek 3).

    Stahuje se jen jednou na CDX `digest` (stejný obsah), ale **každý časový okamžik snímku se zachová** —
    jinak by deduplikace zahodila pozdější snímek se stejným obsahem, který může být jediným potvrzením PIT
    (review ChatGPT k PR #71). Vrací {digest: (fetch_capture, [všechny časy v oknech])}.
    """
    wins = sorted((r - PIT_FETCH_BEFORE, r + PIT_AFTER) for r in releases)
    out = {}
    for cap in captures:
        if any(a <= cap[0] <= b for a, b in wins):
            first, times = out.setdefault(cap[2], (cap, []))
            times.append(cap[0])
    return out


def pit_for_article(code, release, snapshots):
    """snapshots: [(capture_utc, codes_set)]; snímek bez jakéhokoli kódu = nevykreslený ⇒ nevstupuje."""
    obs = [(t, code in codes) for t, codes in snapshots if codes]
    return classify_archive_evidence(release, obs)


# ---------------------------------------------------------------- Binance Vision (čisté funkce)
def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_checksum(zip_bytes: bytes, checksum_text: bytes) -> str:
    want = checksum_text.decode().strip().split()[0].lower() if checksum_text.strip() else ""
    got = sha256(zip_bytes)
    if len(want) != 64 or got != want:
        raise ValueError("CHECKSUM nesouhlasí")
    return got


def open_minutes(zip_bytes: bytes) -> set:
    """Jen časová razítka otevření minut (UTC, int minut od epochy); ceny se NEČTOU."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError("ZIP musí mít právě 1 CSV")
        out, raw, units = set(), set(), {}
        for i, line in enumerate(z.read(names[0]).decode().splitlines()):
            first = line.split(",", 1)[0].strip()
            if i == 0 and first == "open_time":
                continue  # jediná povolená nečíselná řádka = hlavička na 1. řádku
            if not first.isdigit():
                raise ValueError("nečíselný open_time mimo hlavičku")  # fail closed (review ChatGPT k PR #71)
            v = int(first)
            # Only plausible millisecond or microsecond epoch values.
            # Fail closed on off-minute timestamps and duplicates.
            if 1_000_000_000_000 <= v < 10_000_000_000_000:
                unit = 60_000
            elif 1_000_000_000_000_000 <= v < 10_000_000_000_000_000:
                unit = 60_000_000
            else:
                raise ValueError("open_time epoch mimo ms/us rozsah")
            if v % unit:
                raise ValueError("open_time není hranice minuty")
            if units.setdefault("u", unit) != unit:
                raise ValueError("smíšené jednotky ms/µs v jednom souboru")
            if v in raw:
                continue  # přesný duplikát řádku: pro množinu minut neškodný, nic nenafukuje (review Claude k 83306d1)
            raw.add(v)
            out.add(v // unit)
    return out


def _minute(dt):
    return int(dt.timestamp()) // 60


def perp_and_coverage(minutes: set, t_ann: datetime):
    """(perp_ok, coverage_ok_minutes, info) podle PROTOCOL §3.3–3.4; minutes = pokryté okno [−7 d, +14 d]."""
    entry = t_ann + LAG
    # Entry may be at any minute; the required continuous 60m begins at entry,
    # not at the start of its containing UTC hour (PIT/execution feasibility).
    entry_minute = _minute(entry)
    full_hour = all(m in minutes for m in range(entry_minute, entry_minute + 60))
    last = max(minutes) if minutes else None
    perp_ok = bool(full_hour and last is not None and last >= _minute(entry + MIN_AFTER_ENTRY))
    lo, win_hi = _minute(t_ann - COV_BEFORE), _minute(t_ann + COV_AFTER)
    # PROTOCOL §3.4: pokrytí „do perp_last_trade“. Konec obchodování se ale uznává jen s doložením:
    # poslední minuta je UPROSTŘED UTC dne (denní soubor končí před 23:59 ⇒ obchodování skončilo, ne výpadek
    # celých souborů). Jinak (konec 23:59 / žádná data) jmenovatel = celé zmrazené okno (fail closed;
    # review ChatGPT aa88f6a k PR #71). Zbytkové riziko (výpadek uprostřed dne) kryje citlivost v manifestu.
    end_ok = last is not None and last < win_hi - 1 and (last % 1440) != 1439
    hi = last + 1 if end_ok else win_hi

    def _cov(h):
        return sum(1 for m in minutes if lo <= m < h) / max(h - lo, 1)

    cov, cov_full = _cov(hi), _cov(win_hi)
    return perp_ok, cov >= MIN_MINUTE_COVERAGE, {
        "minute_coverage": round(cov, 6), "minute_coverage_full_window": round(cov_full, 6),
        "coverage_truncated_at_last_trade": bool(end_ok),
        "perp_last_minute_utc": None if last is None else datetime.fromtimestamp(last * 60, UTC).isoformat()}


def days(t_ann):
    d, end = (t_ann - COV_BEFORE).date(), (t_ann + COV_AFTER).date()
    while d <= end:
        yield d
        d += timedelta(days=1)


# ---------------------------------------------------------------- síťová vrstva (jen Actions)
class Recorder:
    """Obal fetch: zapíše URL, status a SHA-256 každé odpovědi do manifestu."""

    def __init__(self, fetch, pause=0.0):
        self.fetch, self.pause, self.log = fetch, pause, []

    def __call__(self, url):
        for attempt in range(3):
            status, body = self.fetch(url)
            if status not in (429, 500, 502, 503, 504):
                break
            time.sleep(self.pause * (attempt + 2))
        self.log.append({"url": url, "status": status, "sha256": sha256(body) if status == 200 else None})
        if self.pause:
            time.sleep(self.pause)
        return status, body


def enumerate_cms(get):
    arts, page = [], 1
    while True:
        status, body = get(CMS_LIST.format(page=page))
        if status != 200:
            return None, f"CMS HTTP {status} (strana {page})"
        data = json.loads(body).get("data") or {}
        items = [a for c in data.get("catalogs", []) for a in c.get("articles", [])] or data.get("articles", [])
        if not items:
            return arts, None
        arts += [{"code": a["code"], "title": a["title"],
                  "release": datetime.fromtimestamp(int(a["releaseDate"]) / 1000, UTC)} for a in items]
        page += 1
        if page > 400:
            return None, "CMS stránkování nekonečné"


def load_symbol_minutes(get, sym, t_ann, files):
    """Denní 1m klines symbolu v okně; každý soubor CHECKSUM-ověřen. None = symbol v den t_ann neexistuje."""
    minutes, ok = set(), True
    for d in days(t_ann):
        url = f"{VISION}/daily/klines/{sym}/1m/{sym}-1m-{d.isoformat()}.zip"
        st, z = get(url)
        if st != 200:
            if d == t_ann.date():
                return None, False
            continue  # mimo existenci perpu; pokrytí to zachytí
        st2, ck = get(url + ".CHECKSUM")
        try:
            files.append({"url": url, "sha256": verify_checksum(z, ck if st2 == 200 else b"")})
            minutes |= open_minutes(z)
        except (ValueError, zipfile.BadZipFile):
            ok = False
            files.append({"url": url, "sha256": None, "error": "checksum_or_parse"})
    return minutes, ok


def funding_ok(get, sym, t_ann, files):
    months = sorted({(d.year, d.month) for d in days(t_ann)})
    for y, m in months:
        url = f"{VISION}/monthly/fundingRate/{sym}/{sym}-fundingRate-{y:04d}-{m:02d}.zip"
        st, z = get(url)
        st2, ck = get(url + ".CHECKSUM")
        if st != 200 or st2 != 200:
            return False
        try:
            files.append({"url": url, "sha256": verify_checksum(z, ck)})
        except ValueError:
            return False
    return True


def book_available(get, sym, t_ann):
    """Diagnostika (dialog 0407): ANO/NE existence bezplatné historické knihy v den t_ann; NEFILTRUJE."""
    out = {}
    for kind in ("bookTicker", "bookDepth"):
        url = f"{VISION}/daily/{kind}/{sym}/{sym}-{kind}-{t_ann.date().isoformat()}.zip"
        out[kind] = get(url)[0] == 200
    return out


def collect(fetch, pause=0.0):
    get = Recorder(fetch, pause)
    manifest = {"protocol": "research/k11_delist_drift/PROTOCOL.md (dodatky 1–3)", "returns_computed": False}
    arts, err = enumerate_cms(get)
    if arts is None:
        manifest.update(enumeration_error=err, verdict="DATA_NO_GO", http_log=get.log)
        return [], manifest
    arts = [a for a in arts if WINDOW_START <= a["release"] < WINDOW_END]
    spot = [a for a in arts if classify_title(a["title"]) == "spot_delist"]
    unparsed = [a["code"] for a in spot if parse_tokens(a["title"]) is None]

    captures = []
    for prefix in ARCHIVE_PREFIXES:
        st, body = get(CDX.format(url=prefix))
        if st == 200 and body.strip():
            captures += parse_cdx(json.loads(body))
    snaps = []
    for (t, original, _), times in needed_captures(sorted(set(captures)), [a["release"] for a in spot]).values():
        st, body = get(f"https://web.archive.org/web/{t:%Y%m%d%H%M%S}id_/{original}")
        if st == 200:
            codes = extract_codes(body)
            snaps += [(ti, codes) for ti in times]

    rows, files = [], []
    for a in arts:
        etype = classify_title(a["title"])
        toks = parse_tokens(a["title"]) if etype == "spot_delist" else None
        if etype == "spot_delist" and toks is not None:
            pit, ev = pit_for_article(a["code"], a["release"], snaps)
        for tok in toks or [None]:
            row = {"article_id": a["code"], "token": tok or "", "event_type": etype,
                   "announced_at": a["release"].isoformat().replace("+00:00", "Z"), "title": a["title"]}
            if etype != "spot_delist" or tok is None:
                row["token"] = row["token"] or "UNPARSED"
                if etype == "spot_delist":
                    row["event_type"] = "spot_delist_unparsed"  # vykázáno zvlášť, úplnost řeší dodatek 3
                rows.append(row)
                continue
            perp_sym, minutes, ck_ok = "", None, False
            for pre in PERP_PREFIXES:
                minutes, ck_ok = load_symbol_minutes(get, f"{pre}{tok}USDT", a["release"], files)
                if minutes is not None:
                    perp_sym = f"{pre}{tok}USDT"
                    break
            if minutes is None:
                perp_ok, cov_ok, info, f_ok, book = False, False, {}, False, {}
            else:
                perp_ok, cov_ok, info = perp_and_coverage(minutes, a["release"])
                f_ok = funding_ok(get, perp_sym, a["release"], files)
                book = book_available(get, perp_sym, a["release"])
            row.update(pit_status=pit, pit_ok=pit == "ok", perp_symbol=perp_sym, perp_ok=perp_ok,
                       coverage_ok=bool(cov_ok and ck_ok and f_ok), checksum_ok=ck_ok, funding_ok=f_ok,
                       book_ticker_available=book.get("bookTicker", False),
                       book_depth_available=book.get("bookDepth", False), **info, **ev)
            rows.append(row)

    spot_rows = [r for r in rows if r["event_type"] == "spot_delist"]
    gate = audit_gate(spot_rows)
    # Citlivost (diagnostika, verdikt NEMĚNÍ): co kdyby se pokrytí vždy počítalo přes celé okno [−7 d, +14 d].
    full = [dict(r, coverage_ok=bool(r["coverage_ok"] and r.get("minute_coverage_full_window", 0) >= MIN_MINUTE_COVERAGE))
            for r in spot_rows]
    manifest["gate_sensitivity_full_window"] = audit_gate(full)
    manifest["coverage_truncated_events"] = sum(bool(r.get("coverage_truncated_at_last_trade")) for r in spot_rows)
    unparsed_share = len(unparsed) / len(spot) if spot else 1.0
    verdict = gate["verdict"] if unparsed_share <= MAX_UNPARSED_SHARE else "DATA_NO_GO"
    manifest.update(articles_in_window=len(arts), spot_articles=len(spot), spot_articles_unparsed=unparsed,
                    unparsed_share=round(unparsed_share, 6), archive_captures=len(captures),
                    archive_snapshots_fetched=len(snaps),
                    archive_snapshots_rendered=sum(1 for _, c in snaps if c),
                    event_types={t: sum(r["event_type"] == t for r in rows) for t in sorted({r["event_type"] for r in rows})},
                    gate=gate, verdict=verdict, vision_files=files, http_log=get.log)
    return rows, manifest


COLUMNS = ["article_id", "token", "event_type", "announced_at", "title", "pit_status", "pit_ok", "perp_symbol",
           "perp_ok", "coverage_ok", "checksum_ok", "funding_ok", "minute_coverage", "minute_coverage_full_window",
           "coverage_truncated_at_last_trade", "perp_last_minute_utc",
           "book_ticker_available", "book_depth_available", "observations", "earliest_contradiction_utc",
           "first_corroboration_utc"]


def write_outputs(rows, manifest, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    (outdir / "events.csv").write_text(buf.getvalue())
    manifest["events_csv_sha256"] = sha256(buf.getvalue().encode())
    (outdir / "step0_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True, default=str))
    return manifest


def _urllib_fetch(url):  # pragma: no cover — jen GitHub Actions
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "k11-step0-audit (research, PAPER)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (urllib.error.URLError, TimeoutError):
        return 599, b""


if __name__ == "__main__":  # pragma: no cover
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", default="research/k11_delist_drift")
    out = Path(p.parse_args().outdir)
    rows, man = collect(_urllib_fetch, pause=0.3)
    man = write_outputs(rows, man, out)
    print(json.dumps({k: man.get(k) for k in ("verdict", "gate", "spot_articles", "unparsed_share",
                                              "archive_snapshots_rendered", "enumeration_error")}, default=str))
