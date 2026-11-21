"""Fail-closed PIT evidence preflight for research data sources (no trading signals)."""
from datetime import datetime, timezone
from urllib.parse import urlparse
import re


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def audit_evidence(record, decision_at):
    """Return DATA_NO_GO or PIT_EVIDENCE_PREFLIGHT_ONLY, never DATA_GO.

    first_seen_at must be independently backed by an immutable archive reference;
    this module validates the declaration, not the archive's actual contents.
    """
    if not isinstance(record, dict):
        return {"status": "DATA_NO_GO", "reason": "invalid_record"}
    required = ("source_id", "event_id", "archive_url", "published_at",
                "first_seen_at", "retrieved_at")
    for key in required:
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            return {"status": "DATA_NO_GO", "reason": "missing_or_invalid_" + key}
    url = urlparse(record["archive_url"])
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        return {"status": "DATA_NO_GO", "reason": "invalid_archive_url"}
    # For Wayback snapshots, the URL capture timestamp must not be later than
    # the claimed first-seen time. This is a consistency check, NOT proof that
    # the archive is genuine or that the content existed at that timestamp.
    capture = None
    if url.hostname == "web.archive.org":
        match = re.fullmatch(r"/web/(\\d{14})(?:[a-z_]{0,3})?/(.+)", url.path)
        if match is None:
            return {"status": "DATA_NO_GO", "reason": "invalid_wayback_capture_path"}
        capture = _time(match.group(1)[:4] + "-" + match.group(1)[4:6] + "-" + match.group(1)[6:8]
                        + "T" + match.group(1)[8:10] + ":" + match.group(1)[10:12]
                        + ":" + match.group(1)[12:14] + "Z")
        if capture is None:
            return {"status": "DATA_NO_GO", "reason": "invalid_wayback_capture_timestamp"}
    times = {key: _time(record[key]) for key in ("published_at", "first_seen_at", "retrieved_at")}
    decision = _time(decision_at)
    if decision is None or any(value is None for value in times.values()):
        return {"status": "DATA_NO_GO", "reason": "invalid_timestamp"}
    if capture is not None and capture > times["first_seen_at"]:
        return {"status": "DATA_NO_GO", "reason": "capture_after_claimed_first_seen"}
    if not (times["published_at"] <= times["first_seen_at"] < decision):
        return {"status": "DATA_NO_GO", "reason": "not_available_before_decision"}
    if times["retrieved_at"] < times["first_seen_at"]:
        return {"status": "DATA_NO_GO", "reason": "retrieval_before_archive"}
    return {
        "status": "PIT_EVIDENCE_PREFLIGHT_ONLY",
        "reason": "archive_content_and_independence_unverified",
        "requires": ["archive_content_verification", "source_independence",
                     "event_deduplication", "economic_mechanism", "cost_and_slippage"],
    }
