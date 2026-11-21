"""Fail-closed PIT evidence diversity gate; no trading signals or performance tests.

A mirror, aggregator, or archive copy is NOT an independent publisher.
All timestamps are timezone-aware UTC instants and must precede decision time.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def audit_independent_sources(records, decision_at, min_publishers=2):
    """Return diagnostic only; accepted=True is NOT a DATA-GO decision.

    Each record requires publisher_id, original_source_id, published_at,
    first_captured_at and evidence_url. Original_source_id identifies the
    underlying originating disclosure, not the URL of an archive mirror.
    """
    decision = _utc(decision_at)
    if type(min_publishers) is not int or min_publishers < 2:
        raise ValueError("min_publishers must be integer >= 2")
    if not isinstance(records, (list, tuple)) or not records:
        return {"accepted": False, "independent_publishers": 0, "reasons": ["no_records"]}
    publishers = set()
    origins = set()
    reasons = []
    for index, record in enumerate(records):
        try:
            if not isinstance(record, dict):
                raise ValueError("record_not_dict")
            identifiers = [record.get(k) for k in ("publisher_id", "original_source_id")]
            if any(not isinstance(x, str) or not x.strip() for x in identifiers):
                raise ValueError("missing_identity")
            url = record.get("evidence_url")
            if not isinstance(url, str) or not url.strip():
                raise ValueError("missing_url")
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("invalid_evidence_url")
            published = _utc(record.get("published_at"))
            captured = _utc(record.get("first_captured_at"))
            if published > captured:
                raise ValueError("capture_before_publication")
            if captured >= decision:
                raise ValueError("not_available_at_decision")
            publishers.add(identifiers[0].strip().casefold())
            origins.add(identifiers[1].strip().casefold())
        except (ValueError, TypeError, AttributeError) as exc:
            reasons.append(f"record_{index}:{exc}")
    if len(publishers) < min_publishers:
        reasons.append("insufficient_publishers")
    if len(origins) < min_publishers:
        reasons.append("insufficient_original_sources")
    return {"accepted": not reasons, "independent_publishers": len(publishers),
            "independent_origins": len(origins), "reasons": reasons}
