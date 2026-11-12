"""P3 daily candle adapter: explicit close boundary and auditable provenance.

Pure synthetic/offline contract, no data download. Timestamps and hashes are
supplied evidence, not proof that the provider published the payload then.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re

from .features import DailyClose, build_daily_features, _utc
from .feature_serialization import canonical_feature_record


@dataclass(frozen=True)
class DailyInput:
    symbol: str
    open_time: datetime
    published_at: datetime
    received_at: datetime
    close: float
    provider: str
    dataset_version: str
    quality_flag: str
    payload_sha256: str


def adapt_daily(row: DailyInput, decision: datetime) -> DailyClose:
    """Map a UTC 1d open to exclusive close (open + 1d), never open-as-close."""
    if not all(_utc(t) for t in (row.open_time, row.published_at, row.received_at, decision)):
        raise ValueError("invalid_source_or_timezone")
    if any((row.open_time.hour, row.open_time.minute, row.open_time.second, row.open_time.microsecond)):
        raise ValueError("non_daily_open_boundary")
    if not all(isinstance(v, str) and v.strip() for v in (row.provider, row.dataset_version)):
        raise ValueError("missing_provenance")
    if row.quality_flag != "accepted":
        raise ValueError("quality_excluded")
    if not isinstance(row.payload_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", row.payload_sha256):
        raise ValueError("invalid_payload_hash")
    if type(row.close) not in (int, float) or not math.isfinite(row.close) or row.close <= 0:
        raise ValueError("invalid_close")
    boundary = row.open_time.astimezone(timezone.utc) + timedelta(days=1)
    if max(boundary, row.published_at, row.received_at) >= decision:
        raise ValueError("not_yet_available")
    if row.published_at < boundary or row.received_at < row.published_at:
        raise ValueError("invalid_source_chronology")
    return DailyClose(row.symbol, boundary, row.published_at.astimezone(timezone.utc),
                      row.received_at.astimezone(timezone.utc), float(row.close))


def build_feature_bundle(xrp: list[DailyInput], btc: list[DailyInput], decision: datetime) -> tuple[bytes, str]:
    """Validate inputs -> real P2 features -> canonical features + source manifest.

    All 62 input records are retained, sorted by symbol/open time. Fail closed
    on invalid inputs; callers must record exclusions instead of filling gaps.
    Volatility is unannualized population std. of daily log returns.
    """
    for series in (xrp, btc):
        if len({r.provider for r in series}) > 1:
            raise ValueError("mixed_provider_in_symbol_series")
    features = build_daily_features([adapt_daily(r, decision) for r in xrp],
                                    [adapt_daily(r, decision) for r in btc], decision)
    feature_bytes, feature_hash = canonical_feature_record(features)
    sources = []
    for row in sorted(xrp + btc, key=lambda r: (r.symbol, r.open_time)):
        source = asdict(row)
        source["close"] = float(row.close)
        for key in ("open_time", "published_at", "received_at"):
            source[key] = source[key].astimezone(timezone.utc).isoformat()
        source["close_boundary"] = (row.open_time.astimezone(timezone.utc) + timedelta(days=1)).isoformat()
        sources.append(source)
    result = {"schema_version": "radar-feature-bundle-v1", "features": json.loads(feature_bytes),
              "feature_sha256": feature_hash, "sources": sources}
    payload = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return payload, hashlib.sha256(payload).hexdigest()
