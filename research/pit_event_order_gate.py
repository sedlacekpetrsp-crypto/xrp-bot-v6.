"""Fail-closed PIT chronology screen; NOT proof of source independence or profitability."""
from datetime import datetime, timezone


def _utc(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be nonempty ISO-8601 string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def assess_event(event, decision_at):
    """Screen chronological consistency only; independent evidence remains mandatory."""
    required = ("event_id", "published_at", "first_seen_at", "effective_at",
                "source_id", "archive_id")
    if not isinstance(event, dict) or any(
        not isinstance(event.get(k), str) or not event[k].strip() for k in required
    ):
        return {"status": "DATA_NO_GO", "reason": "missing_evidence"}
    try:
        decision = _utc(decision_at)
        published = _utc(event["published_at"])
        seen = _utc(event["first_seen_at"])
        effective = _utc(event["effective_at"])
    except (ValueError, TypeError, OverflowError):
        return {"status": "DATA_NO_GO", "reason": "invalid_timestamp"}
    if published > seen:
        return {"status": "DATA_NO_GO", "reason": "publication_after_capture"}
    if seen > decision:
        return {"status": "DATA_NO_GO", "reason": "not_known_at_decision"}
    if effective < published:
        return {"status": "DATA_NO_GO", "reason": "effective_before_publication"}
    return {"status": "PIT_TIME_PASS_ONLY", "reason": "requires_source_and_cost_audit"}
