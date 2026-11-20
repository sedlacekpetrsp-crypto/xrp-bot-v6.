"""Data-only audit: archive captures are not independent source attestations.

No market prices, trading rules, backtest, or PnL are used here.
"""
from datetime import datetime, timezone


def _time(value):
    if not isinstance(value, str):
        raise ValueError("invalid_timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("naive_timestamp")
    return parsed.astimezone(timezone.utc)


def independent_source_gate(records, *, decision_at, min_sources=2):
    """Fail closed unless >= min_sources distinct origin publishers existed as-of decision.

    Multiple archive snapshots, URLs or mirrors of the same publisher count once.
    This checks *claimed* metadata consistency, not cryptographic authenticity.
    """
    if not isinstance(records, list) or isinstance(min_sources, bool) or not isinstance(min_sources, int) or min_sources < 2:
        raise ValueError("invalid_input")
    decision = _time(decision_at)
    origins = {}
    for record in records:
        if not isinstance(record, dict):
            return {"status": "DATA_NO_GO", "reason": "bad_record"}
        required = ("origin", "source_id", "published_at", "captured_at", "content_hash")
        if any(not isinstance(record.get(k), str) or not record[k].strip() for k in required):
            return {"status": "DATA_NO_GO", "reason": "missing_provenance"}
        try:
            published, captured = _time(record["published_at"]), _time(record["captured_at"])
        except ValueError:
            return {"status": "DATA_NO_GO", "reason": "bad_timestamp"}
        if published > captured or captured > decision:
            return {"status": "DATA_NO_GO", "reason": "not_available_asof"}
        origin = record["origin"].strip().lower()
        if origin in origins and origins[origin] != record["content_hash"]:
            return {"status": "DATA_NO_GO", "reason": "conflicting_origin_snapshots"}
        origins[origin] = record["content_hash"]
    return {"status": "DATA_GO" if len(origins) >= min_sources else "DATA_NO_GO",
            "reason": "independent_origin_count" if len(origins) >= min_sources else "insufficient_independent_origins",
            "independent_origins": len(origins), "performance_authorized": False}
