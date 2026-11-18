"""K10 archived-label byte-integrity gate (DATA ONLY, no returns or trading).

A matching digest verifies bytes, not the truth of an exchange attribution or
authenticity of the archive's capture timestamp. Independent source attestation
and pre-sample cohort evidence remain mandatory.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from urllib.parse import urlsplit
import re

_HEX = re.compile(r"^[0-9a-f]{64}$")
_WAYBACK = re.compile(r"^/web/(\\d{14})id_/https?://[^/]+(?:/.*)?$")


@dataclass(frozen=True)
class Snapshot:
    source_url: str
    captured_at: datetime
    decision_at: datetime
    expected_sha256: str
    content: bytes


def verify_snapshot(snapshot: Snapshot) -> str:
    """Fail closed on malformed provenance, post-decision capture, or altered bytes.

    Returns the verified digest; does not label any account or permit performance.
    """
    if not isinstance(snapshot, Snapshot):
        raise ValueError("invalid snapshot")
    for t in (snapshot.captured_at, snapshot.decision_at):
        if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
            raise ValueError("timestamps must be timezone-aware UTC")
    if snapshot.captured_at >= snapshot.decision_at:
        raise ValueError("archive captured after decision")
    if not isinstance(snapshot.source_url, str):
        raise ValueError("invalid source URL")
    try:
        url = urlsplit(snapshot.source_url)
        if url.scheme != "https" or url.hostname != "web.archive.org" or url.username or url.password or url.fragment or url.query or url.port not in (None, 443):
            raise ValueError("source must be an uncredentialed HTTPS URL")
    except ValueError as exc:
        raise ValueError("invalid source URL") from exc
    match = _WAYBACK.fullmatch(url.path)
    if match is None:
        raise ValueError("source must be a raw Wayback id_ snapshot URL")
    try:
        archive_time = datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid Wayback timestamp") from exc
    if archive_time != snapshot.captured_at:
        raise ValueError("declared capture time differs from archive URL")
    if not isinstance(snapshot.expected_sha256, str) or not _HEX.fullmatch(snapshot.expected_sha256):
        raise ValueError("invalid SHA-256 digest")
    if not isinstance(snapshot.content, bytes) or not snapshot.content:
        raise ValueError("missing immutable snapshot bytes")
    actual = sha256(snapshot.content).hexdigest()
    if not compare_digest(actual, snapshot.expected_sha256):
        raise ValueError("snapshot byte-integrity mismatch")
    return actual
