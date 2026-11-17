"""Research-only fail-closed PIT input manifest verification (no performance run)."""
from datetime import datetime
from hashlib import sha256
from pathlib import Path

def utc(s):
    if not isinstance(s, str):
        raise ValueError("timestamp must be string")
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset().total_seconds() != 0:
        raise ValueError("explicit UTC required")
    return d

def verify(manifest, root, cutoff):
    decision = utc(cutoff)
    inputs = manifest.get("inputs") if isinstance(manifest, dict) else None
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("nonempty inputs required")
    root = Path(root).resolve()
    seen = set()
    for item in inputs:
        if not isinstance(item, dict):
            raise ValueError("invalid item")
        name = item.get("path")
        if not isinstance(name, str) or not name or name in seen:
            raise ValueError("duplicate or invalid path")
        seen.add(name)
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("missing or escaped path")
        known = utc(item.get("known_at"))
        event = utc(item.get("event_at"))
        if known > decision or event > known:
            raise ValueError("PIT violation; preannouncements require separate schema")
        digest = item.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid sha256")
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("hash mismatch")
    return {"status": "PASS", "checked_inputs": len(seen)}
