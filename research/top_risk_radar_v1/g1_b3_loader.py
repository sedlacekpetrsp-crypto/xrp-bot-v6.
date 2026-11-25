"""G1 bloker B3: real 1m -> daily XRP+BTC loader with per-row PIT and provenance.

PURE / OFFLINE. No network, no download, no fitting, no predictions, no trading.
Input = already-verified Binance Vision spot 1m kline CSV lines + the SHA-256 of
the archive they came from (download + .CHECKSUM verification belong to the G0
data run, bloker B4). Output = one auditable row per G1 decision day:
9 frozen B3 features (manifest v1 par. 5), reference price, 14 d risk label or an
explicit exclusion reason. Nothing is ever imputed or forward-filled.

Contracts (freeze manifest v1 par. 3, revision 0326 blocks A/B; G1_PIT_0005_BOUNDARY_QA):
  * Decision grid key = 00:05:00 UTC (canonical ``validate_g1_decisions``).
    Completed-bar contract: effective decision_at = 00:06:00 UTC (end of the
    00:05 minute). P(t) = CLOSE of the 00:05 1m bar with trades > 0, otherwise
    the row is excluded ``no_trade_in_minute_0005``.
  * Label window = 1m bars with open_time in [00:06, 00:06 + 336 h). Positive iff
    any LOW <= 0.8 * P(t). Any missing minute in the window =>
    ``missing_minutes_in_horizon``. Window not fully observed by ``as_of`` =>
    ``unmatured`` (positives and negatives treated identically, block B).
  * Features: daily close for boundary B (00:00 UTC) = CLOSE of the 23:59 bar of
    the previous day; if that 23:59 bar is absent the daily close is missing and
    every decision needing it is excluded ``incomplete_daily_bar`` (features use
    closes only, so intraday gaps elsewhere in the day are reported by G0 QA,
    not used to drop days -- Q38).
    Availability of a historical archive row is a property of the ROW, not of
    the download time: published_at = boundary + 60 s (rule ``close_plus_60s``),
    which must be strictly before the 00:05 grid key (checked by ``adapt_daily``).
    ``retrieved_at`` of the archive is evidence only (review C2 of a98099c).
  * Feature builder = existing ``feature_input.build_feature_bundle`` (P2/P3,
    reused, not re-implemented) + ``btc_realized_vol_30d`` which manifest v1
    par. 5 requires for B3 but ``features.py`` does not emit (computed here with
    the identical population-std formula; flagged for review, Q38).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Sequence

from research.top_risk_radar_v1.binance_spot_trades import epoch_to_utc
from research.top_risk_radar_v1.feature_input import DailyInput, build_feature_bundle
from research.top_risk_radar_v1.g1_decision_input import validate_g1_decisions

UTC = timezone.utc
MINUTE = timedelta(minutes=1)
DAY = timedelta(days=1)
HORIZON = timedelta(hours=336)
RISK_RATIO = 0.8
PUBLICATION_LAG = timedelta(seconds=60)
LOOKBACK_DAYS = 31
PROVIDER = "binance-vision-spot-klines-1m"
LOADER_VERSION = "g1-b3-loader-v1"
SYMBOLS = ("XRPUSDT", "BTCUSDT")

# Manifest v1 par. 5, B3 (Model A) -- order frozen; B1 = rv30, B2 = ret7, ret30, dd30.
B3_FEATURES = (
    "xrp_realized_vol_7d", "xrp_realized_vol_30d", "xrp_log_return_1d", "xrp_log_return_7d",
    "xrp_log_return_30d", "xrp_drawdown_30d", "relative_log_return_30d", "btc_log_return_7d",
    "btc_realized_vol_30d",
)
B1_FEATURES = ("xrp_realized_vol_30d",)
B2_FEATURES = ("xrp_log_return_7d", "xrp_log_return_30d", "xrp_drawdown_30d")

EXCLUSION_REASONS = (
    "decision_after_as_of", "incomplete_daily_bar", "no_trade_in_minute_0005", "missing_minutes_in_horizon", "unmatured",
)


class LoaderError(ValueError):
    """Structural data defect => G0 INVALID_RUN (never a per-row exclusion)."""


@dataclass(frozen=True)
class Bar:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    trades: int
    archive_sha256: str


def _price(text: str, where: str) -> float:
    try:
        v = float(text)
    except ValueError as exc:
        raise LoaderError(f"{where}: non-numeric price") from exc
    if not math.isfinite(v) or v <= 0:
        raise LoaderError(f"{where}: price must be finite and > 0")
    return v


def parse_klines_1m(lines: Iterable[str], archive_sha256: str) -> list[Bar]:
    """Binance Vision 1m kline CSV (12 columns) -> bars; fail closed on any defect.

    ms (< 2025) and us (>= 2025) timestamps are both accepted via the shared
    ``epoch_to_utc`` magnitude rule. Gaps are allowed here (reported later);
    duplicates, disorder, wrong close_time and OHLC violations are not.
    """
    if not isinstance(archive_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", archive_sha256):
        raise LoaderError("archive_sha256 must be 64 lowercase hex")
    bars: list[Bar] = []
    for n, row in enumerate(csv.reader(lines), 1):
        if not row:
            continue
        if n == 1 and row[0].strip().lower() in ("open_time", "open time"):
            continue
        where = f"row {n}"
        if len(row) != 12:
            raise LoaderError(f"{where}: expected 12 columns")
        try:
            t = epoch_to_utc(row[0].strip())
            close_t = epoch_to_utc(row[6].strip())
        except ValueError as exc:
            raise LoaderError(f"{where}: {exc}") from exc
        if t.second or t.microsecond:
            raise LoaderError(f"{where}: open_time not on a minute boundary")
        if not (t + MINUTE - timedelta(milliseconds=1) <= close_t < t + MINUTE):
            raise LoaderError(f"{where}: close_time inconsistent with 1m bar")
        o, h, lo, c = (_price(row[i], where) for i in (1, 2, 3, 4))
        if lo > min(o, c) or h < max(o, c) or lo > h:
            raise LoaderError(f"{where}: OHLC sanity")
        if not row[8].strip().isdigit():
            raise LoaderError(f"{where}: trades must be a non-negative integer")
        if bars and t <= bars[-1].open_time:
            raise LoaderError(f"{where}: duplicate or out-of-order minute")
        bars.append(Bar(t, o, h, lo, c, int(row[8]), archive_sha256))
    return bars


class MinuteSeries:
    """Indexed 1m bars of one symbol, assembled from verified monthly archives."""

    def __init__(self, symbol: str, bars: Sequence[Bar]):
        if symbol not in SYMBOLS:
            raise LoaderError(f"unsupported symbol {symbol!r}")
        self.symbol = symbol
        self._by_time: dict[datetime, Bar] = {}
        for b in bars:
            if b.open_time in self._by_time:
                raise LoaderError(f"{symbol}: duplicate minute {b.open_time.isoformat()} across archives")
            self._by_time[b.open_time] = b
        if not self._by_time:
            raise LoaderError(f"{symbol}: empty series")
        self.last_open = max(self._by_time)

    def get(self, t: datetime) -> Bar | None:
        return self._by_time.get(t)

    def count_missing(self, start: datetime, end: datetime) -> int:
        n, t = 0, start
        while t < end:
            n += t not in self._by_time
            t += MINUTE
        return n

    def daily_input(self, boundary: datetime) -> DailyInput | None:
        """Daily bar closing at ``boundary`` (00:00 UTC) or None if the day is incomplete."""
        day_start = boundary - DAY
        last = self._by_time.get(boundary - MINUTE)
        if last is None:
            return None
        published = boundary + PUBLICATION_LAG
        return DailyInput(self.symbol, day_start, published, published, last.close, PROVIDER,
                          LOADER_VERSION, "accepted", last.archive_sha256)


def _population_std(values: Sequence[float]) -> float:
    mean = math.fsum(values) / len(values)
    return math.sqrt(math.fsum((v - mean) ** 2 for v in values) / len(values))


def _features(xrp: MinuteSeries, btc: MinuteSeries, key: datetime):
    boundaries = [key.replace(minute=0) - DAY * i for i in range(LOOKBACK_DAYS - 1, -1, -1)]
    rows = {}
    for s in (xrp, btc):
        rows[s.symbol] = [s.daily_input(b) for b in boundaries]
        if any(r is None for r in rows[s.symbol]):
            return None, None
    payload, digest = build_feature_bundle(rows["XRPUSDT"], rows["BTCUSDT"], key)
    bundle = json.loads(payload)
    feats = dict(bundle["features"])
    closes = [r.close for r in rows["BTCUSDT"]]
    feats["btc_realized_vol_30d"] = _population_std(
        [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))])
    sources = sorted({r.payload_sha256 for s in SYMBOLS for r in rows[s]})
    return feats, {"feature_bundle_sha256": digest, "source_archive_sha256": sources,
                   "max_available_at_utc": bundle["features"]["max_available_at_utc"]}


def _label(xrp: MinuteSeries, key: datetime, as_of: datetime):
    """-> (reference_price, y, reason, reference_provenance, label_provenance).

    Caller guarantees decision_at (key + 1 min) <= as_of, so the reference bar is
    observable. Maturity is checked before any horizon bar is read; label
    provenance covers the FULL window (also after an early hit) and is kept
    apart from feature provenance so label metadata never enters a fit.
    """
    ref_bar = xrp.get(key)
    if ref_bar is None or ref_bar.trades == 0:
        return None, None, "no_trade_in_minute_0005", None, None
    ref_prov = {"archive_sha256": ref_bar.archive_sha256, "bar_open_utc": key.isoformat()}
    start = key + MINUTE
    end = start + HORIZON
    if end > as_of:
        return ref_bar.close, None, "unmatured", ref_prov, None
    if xrp.count_missing(start, end):
        return ref_bar.close, None, "missing_minutes_in_horizon", ref_prov, None
    barrier = RISK_RATIO * ref_bar.close
    y, shas, t = 0, set(), start
    while t < end:
        bar = xrp.get(t)
        shas.add(bar.archive_sha256)
        if bar.low <= barrier:
            y = 1
        t += MINUTE
    label_prov = {"archive_sha256": sorted(shas), "first_bar_utc": start.isoformat(),
                  "last_bar_utc": (end - MINUTE).isoformat()}
    return ref_bar.close, y, None, ref_prov, label_prov


def build_g1_rows(xrp: MinuteSeries, btc: MinuteSeries, decisions: Sequence[datetime],
                  as_of: datetime) -> list[dict]:
    """One row per decision key; usable rows carry 9 features + y, others an exclusion reason.

    ``as_of`` = last proven observation time (end of the last verified minute),
    never ``now``; a label window ending after it is ``unmatured``.
    """
    if xrp.symbol != "XRPUSDT" or btc.symbol != "BTCUSDT":
        raise LoaderError("series must be (XRPUSDT, BTCUSDT)")
    validate_g1_decisions(decisions)
    if not isinstance(as_of, datetime) or as_of.utcoffset() != timedelta(0):
        raise LoaderError("as_of must be timezone-aware UTC")
    if as_of > xrp.last_open + MINUTE:
        raise LoaderError("as_of is later than the last observed XRP minute")
    out = []
    for key in decisions:
        row = {"decision_key_utc": key.isoformat(), "decision_at_utc": (key + MINUTE).isoformat(),
               "loader_version": LOADER_VERSION}
        if key + MINUTE > as_of:
            # Review 6053223820 (1): nothing observed after as_of may be emitted.
            row.update(status="excluded", reason="decision_after_as_of")
            out.append(row)
            continue
        feats, prov = _features(xrp, btc, key)
        if feats is None:
            row.update(status="excluded", reason="incomplete_daily_bar")
            out.append(row)
            continue
        ref, y, reason, ref_prov, label_prov = _label(xrp, key, as_of)
        row.update({"features": {k: feats[k] for k in B3_FEATURES},
                    "provenance": {"features": prov, "reference": ref_prov, "label": label_prov},
                    "reference_price": ref})
        if reason:
            row.update(status="excluded", reason=reason)
        else:
            row.update(status="usable", y=y,
                       label_window_utc=[(key + MINUTE).isoformat(), (key + MINUTE + HORIZON).isoformat()])
        out.append(row)
    return out


def exclusion_summary(rows: Sequence[Mapping]) -> dict:
    counts = {r: 0 for r in EXCLUSION_REASONS}
    usable = positives = 0
    for r in rows:
        if r["status"] == "usable":
            usable += 1
            positives += r["y"]
        else:
            counts[r["reason"]] += 1
    return {"rows": len(rows), "usable": usable, "positives": positives, "excluded": counts}


def rows_sha256(rows: Sequence[Mapping]) -> str:
    payload = json.dumps(list(rows), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()
