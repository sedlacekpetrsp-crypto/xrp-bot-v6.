"""Offline K10 evidence provenance gate; never proves exchange ownership."""
import hashlib
import json
from datetime import datetime, timezone

def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("naive timestamp")
    return t.astimezone(timezone.utc)

def manifest(records, cutoff):
    limit = parse_time(cutoff)
    fields = ("address", "publisher", "source_url", "observed_at", "sha256")
    seen, normalized = set(), []
    for r in records:
        if not isinstance(r, dict) or any(not isinstance(r.get(k), str) or not r[k].strip() for k in fields):
            raise ValueError("missing provenance")
        if parse_time(r["observed_at"]) > limit:
            raise ValueError("future evidence")
        digest = r["sha256"].lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("bad digest")
        key = (r["address"], r["publisher"], r["source_url"])
        if key in seen:
            raise ValueError("duplicate identity")
        seen.add(key)
        normalized.append({**{k: r[k] for k in fields}, "observed_at": parse_time(r["observed_at"]).isoformat(), "sha256": digest})
    if not normalized:
        raise ValueError("empty evidence")
    normalized.sort(key=lambda r: tuple(r[k] for k in fields))
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {"count": len(normalized), "sha256": hashlib.sha256(payload).hexdigest(),
            "records": normalized, "status": "INTEGRITY_ONLY_NOT_DATA_GO"}
