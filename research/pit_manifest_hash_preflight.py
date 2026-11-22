"""Fail-closed, non-performance preflight for immutable research input manifests.

A manifest is a list of {"path": relative/path, "sha256": lowercase hex,
"asof_utc": ISO-8601 UTC timestamp}. No file bytes or trading data are read.
"""
import datetime as dt
import re
from pathlib import PurePosixPath

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_UTC = dt.timezone.utc


def validate_manifest(records, decision_at):
    """Return (ok, errors). Never treat metadata alone as proof of PIT."""
    errors = []
    if not isinstance(records, list) or not records:
        return False, ["empty_or_invalid_manifest"]
    if not isinstance(decision_at, dt.datetime) or decision_at.tzinfo is None:
        return False, ["invalid_decision_time"]
    decision = decision_at.astimezone(_UTC)
    seen = set()
    for i, record in enumerate(records):
        prefix = f"record[{i}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}:invalid_record")
            continue
        path = record.get("path")
        if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
            errors.append(f"{prefix}:invalid_path")
        else:
            parts = path.split("/")
            if any(p in ("", ".", "..") for p in parts) or PurePosixPath(path).is_absolute():
                errors.append(f"{prefix}:invalid_path")
            elif path in seen:
                errors.append(f"{prefix}:duplicate_path")
            else:
                seen.add(path)
        digest = record.get("sha256")
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            errors.append(f"{prefix}:invalid_sha256")
        stamp = record.get("asof_utc")
        try:
            if not isinstance(stamp, str) or not stamp.endswith("Z"):
                raise ValueError("timestamp must end in Z")
            parsed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if parsed.utcoffset() != dt.timedelta(0):
                raise ValueError("not UTC")
            if parsed > decision:
                errors.append(f"{prefix}:future_evidence")
        except (ValueError, TypeError, OverflowError):
            errors.append(f"{prefix}:invalid_asof")
    return not errors, errors
