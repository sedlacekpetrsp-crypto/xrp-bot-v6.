"""Strict claim-scoped PIT source-independence gate. Data-only; no performance tests."""
from datetime import datetime, timezone

ARCHIVE_HOSTS = frozenset({"web.archive.org", "archive.org", "archive.today", "archive.ph"})


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("bad_timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("bad_timestamp") from exc
    if dt.tzinfo is None:
        raise ValueError("bad_timestamp")
    return dt.astimezone(timezone.utc)


def gate(records, *, decision_at, claim_id, aliases=None, min_sources=2):
    """Count independent primary publishers, not archive mirrors or syndications.

    published_at is unverified publisher metadata; captured_at bounds knowledge.
    A caller must supply evidence for exactly one claim, and pre-register aliases.
    """
    def no(reason):
        return {"status": "DATA_NO_GO", "reason": reason,
                "independent_origins": 0, "performance_authorized": False}
    if not isinstance(records, list) or not isinstance(claim_id, str) or not claim_id.strip():
        raise ValueError("invalid_input")
    if type(min_sources) is not int or min_sources < 2:
        raise ValueError("invalid_min_sources")
    if aliases is None:
        aliases = {}
    if not isinstance(aliases, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in aliases.items()):
        raise ValueError("invalid_aliases")
    decision = parse_time(decision_at)
    by_origin, hashes, captures = {}, {}, []
    for r in records:
        if not isinstance(r, dict):
            return no("bad_record")
        required = ("origin_publisher", "archive_custodian", "source_id", "content_hash",
                    "captured_at", "published_at", "claim_id", "derived_from")
        if any(k not in r for k in required):
            return no("missing_provenance")
        if any(not isinstance(r[k], str) or not r[k].strip()
               for k in required if k != "derived_from"):
            return no("missing_provenance")
        if r["derived_from"] is not None and (not isinstance(r["derived_from"], str) or not r["derived_from"].strip()):
            return no("missing_lineage")
        if r["claim_id"] != claim_id:
            return no("mixed_claims")
        origin = r["origin_publisher"].strip().lower()
        origin = aliases.get(origin, origin).strip().lower()
        if not origin or origin in ARCHIVE_HOSTS:
            return no("archive_as_publisher")
        parent = r["derived_from"]
        if parent is not None:
            parent = parent.strip().lower()
            parent = aliases.get(parent, parent).strip().lower()
            if not parent or parent in ARCHIVE_HOSTS:
                return no("bad_lineage")
        try:
            published, captured = parse_time(r["published_at"]), parse_time(r["captured_at"])
        except ValueError:
            return no("bad_timestamp")
        if published > captured or captured > decision:
            return no("not_available_asof")
        captures.append(captured)
        signature = (r["content_hash"], parent)
        if origin in by_origin and by_origin[origin] != signature:
            return no("conflicting_origin_snapshots")
        by_origin[origin] = signature
        if r["content_hash"] in hashes and hashes[r["content_hash"]] != origin:
            return no("syndicated_content")
        hashes[r["content_hash"]] = origin
    for origin in by_origin:
        visited = set()
        node = origin
        while node in by_origin and by_origin[node][1] is not None:
            if node in visited:
                return no("lineage_cycle")
            visited.add(node)
            node = by_origin[node][1]
        if node not in by_origin:
            return no("unverified_primary_origin")
    roots = {origin for origin, (_, parent) in by_origin.items() if parent is None}
    count = len(roots)
    return {"status": "DATA_GO" if count >= min_sources else "DATA_NO_GO",
            "reason": "independent_primary_origins" if count >= min_sources else "insufficient_independent_origins",
            "independent_origins": count,
            "asof_bound": max(captures).isoformat() if captures else None,
            "performance_authorized": False}
