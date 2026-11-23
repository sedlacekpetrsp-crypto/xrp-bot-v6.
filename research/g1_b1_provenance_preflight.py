"""G1 B1 provenance preflight. Research-only; no performance evaluation.

The hash proves byte identity, not truth of the external source.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json


class ProvenanceError(ValueError):
    pass


def _utc(value):
    if not isinstance(value, str):
        raise ProvenanceError("timestamp must be ISO8601 string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProvenanceError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ProvenanceError("timezone required")
    return dt.astimezone(timezone.utc)


def audit_b1(manifest, root, decision_at):
    """Fail closed on missing bytes, ambiguous provenance and post-decision availability.

    manifest: list of {path, sha256, source_url, published_at, observed_at}.
    Every row must be available strictly before decision_at. Paths stay within root.
    Returns verified file count; no market signals or performance metrics.
    """
    if not isinstance(manifest, list) or not manifest:
        raise ProvenanceError("nonempty manifest required")
    cutoff = _utc(decision_at)
    base = Path(root).resolve(strict=True)
    seen = set()
    for row in manifest:
        if not isinstance(row, dict) or set(row) != {
            "path", "sha256", "source_url", "published_at", "observed_at"
        }:
            raise ProvenanceError("provenance fields missing or unexpected")
        rel = row["path"]
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
            raise ProvenanceError("invalid relative path")
        target = (base / rel).resolve(strict=True)
        if not target.is_relative_to(base) or not target.is_file() or target.is_symlink():
            raise ProvenanceError("unsafe path")
        if target in seen:
            raise ProvenanceError("duplicate file")
        seen.add(target)
        if not isinstance(row["source_url"], str) or not row["source_url"].startswith("https://"):
            raise ProvenanceError("source URL required")
        published, observed = _utc(row["published_at"]), _utc(row["observed_at"])
        if published > observed or observed >= cutoff:
            raise ProvenanceError("PIT unavailable or impossible order")
        digest = row["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ProvenanceError("invalid digest")
        if sha256(target.read_bytes()).hexdigest() != digest:
            raise ProvenanceError("byte hash mismatch")
    return len(seen)
