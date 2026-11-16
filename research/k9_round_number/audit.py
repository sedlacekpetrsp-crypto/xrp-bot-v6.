"""K9 krok 0: datový audit Binance Vision UM klines 1m (bez výnosů, bez výpočtu fáze A).

Brány podle PROTOCOL.md (zmrazeno 2026-11-16):
- každý měsíc × aktivum: ZIP + CHECKSUM, SHA-256 shoda 100 %;
- ≥ 99 % minut v kalendářním měsíci, jinak měsíc vyloučit a vykázat;
- < 90 % způsobilých měsíců (souhrnně přes aktiva) ⇒ DATA NO-GO.

Modul je čistý: síťové stažení dělá jen `download_month` (volitelné, pro Actions); ostatní funkce
pracují s lokálními soubory, aby šly testovat synteticky.
"""
from __future__ import annotations

import calendar
import hashlib
import io
import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

ASSETS = ("BTCUSDT", "ETHUSDT", "XRPUSDT")
START = (2020, 1)
END = (2026, 10)
DEV_END = pd.Timestamp("2024-01-01", tz="UTC")  # vývoj 2020-01..2023-12, závěrečný úsek 2024-01..2026-10
BASE_URL = "https://data.binance.vision/data/futures/um/monthly/klines/{sym}/1m/{sym}-1m-{y:04d}-{m:02d}.zip"
MIN_MINUTE_COVERAGE = 0.99
MIN_MONTH_SHARE = 0.90
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
              "count", "taker_buy", "taker_buy_quote", "ignore"]


def months(start=START, end=END):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def month_url(sym: str, y: int, m: int) -> str:
    return BASE_URL.format(sym=sym, y=y, m=m)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_checksum(text: str) -> str:
    """CHECKSUM soubor Vision má tvar '<sha256>  <jméno.zip>'."""
    token = text.strip().split()[0].lower() if text.strip() else ""
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        raise ValueError("neplatný CHECKSUM")
    return token


def _to_utc(series: pd.Series) -> pd.DatetimeIndex:
    v = pd.to_numeric(series, errors="raise").astype("int64")
    unit = "us" if v.max() > 10**14 else "ms"  # Vision přešel u části datasetů na mikrosekundy
    return pd.DatetimeIndex(pd.to_datetime(v, unit=unit, utc=True))


def read_kline_zip(path: Path) -> pd.DataFrame:
    """Načte ZIP s jedním CSV (s hlavičkou i bez ní) ⇒ DataFrame s indexem open_time (UTC)."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"ZIP musí obsahovat právě 1 CSV, má {len(names)}")
        raw = z.read(names[0]).decode()
    first = raw.split("\n", 1)[0]
    header = 0 if first.startswith("open_time") else None
    df = pd.read_csv(io.StringIO(raw), header=header, names=None if header == 0 else KLINE_COLS)
    df.columns = KLINE_COLS[: len(df.columns)]
    idx = _to_utc(df["open_time"])
    out = df[["high", "low", "close", "volume", "taker_buy"]].astype(float)
    out.index = idx
    out = out[~out.index.duplicated(keep="first")].sort_index()
    return out


@dataclass
class MonthAudit:
    symbol: str
    month: str
    url: str
    status: str  # OK | MISSING | CHECKSUM_FAIL | LOW_COVERAGE | PARSE_FAIL
    sha256: str = ""
    expected_minutes: int = 0
    present_minutes: int = 0
    coverage: float = 0.0
    out_of_month_rows: int = 0


def audit_month(sym: str, y: int, m: int, zip_path: Path | None, checksum_path: Path | None) -> MonthAudit:
    url = month_url(sym, y, m)
    tag = f"{y:04d}-{m:02d}"
    expected = calendar.monthrange(y, m)[1] * 1440
    rec = MonthAudit(sym, tag, url, "MISSING", expected_minutes=expected)
    if zip_path is None or checksum_path is None or not Path(zip_path).exists() or not Path(checksum_path).exists():
        return rec
    rec.sha256 = sha256_file(Path(zip_path))
    try:
        want = parse_checksum(Path(checksum_path).read_text())
    except ValueError:
        rec.status = "CHECKSUM_FAIL"
        return rec
    if rec.sha256 != want:
        rec.status = "CHECKSUM_FAIL"  # checksum se ověřuje PŘED parsováním obsahu
        return rec
    try:
        df = read_kline_zip(Path(zip_path))
    except Exception:  # noqa: BLE001 — jakákoli chyba formátu = měsíc nezpůsobilý
        rec.status = "PARSE_FAIL"
        return rec
    lo = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
    hi = lo + pd.offsets.MonthBegin(1)
    inside = df[(df.index >= lo) & (df.index < hi)]
    rec.out_of_month_rows = int(len(df) - len(inside))
    rec.present_minutes = int(inside.index.floor("min").nunique())
    rec.coverage = rec.present_minutes / expected
    rec.status = "OK" if rec.coverage >= MIN_MINUTE_COVERAGE else "LOW_COVERAGE"
    return rec


def gate(records: list[MonthAudit]) -> dict:
    """Souhrnná brána kroku 0. Vrací verdikt + seznam vyloučených měsíců (nic se neimputuje)."""
    total = len(records)
    ok = [r for r in records if r.status == "OK"]
    share = len(ok) / total if total else 0.0
    per_asset = {}
    for sym in sorted({r.symbol for r in records}):
        rs = [r for r in records if r.symbol == sym]
        per_asset[sym] = {"months": len(rs), "ok": sum(r.status == "OK" for r in rs)}
    return {
        "verdict": "DATA GO" if total and share >= MIN_MONTH_SHARE else "DATA NO-GO",
        "ok_months": len(ok),
        "total_months": total,
        "ok_share": round(share, 6),
        "per_asset": per_asset,
        "excluded": [{"symbol": r.symbol, "month": r.month, "status": r.status, "coverage": round(r.coverage, 6)}
                     for r in records if r.status != "OK"],
    }


def write_manifest(records: list[MonthAudit], out: Path) -> dict:
    g = gate(records)
    payload = {"protocol": "research/k9_round_number/PROTOCOL.md", "step": "0", "gate": g,
               "months": [asdict(r) for r in records]}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    return g


def download_month(sym: str, y: int, m: int, dest: Path) -> tuple[Path | None, Path | None]:  # pragma: no cover
    """Stáhne ZIP + CHECKSUM (jen v Actions). 404 ⇒ (None, None) — měsíc se vykáže jako MISSING."""
    import urllib.error
    import urllib.request

    dest.mkdir(parents=True, exist_ok=True)
    url = month_url(sym, y, m)
    out = []
    for u in (url, url + ".CHECKSUM"):
        p = dest / u.rsplit("/", 1)[1]
        try:
            with urllib.request.urlopen(u, timeout=120) as r:
                p.write_bytes(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, None
            raise
        out.append(p)
    return out[0], out[1]
