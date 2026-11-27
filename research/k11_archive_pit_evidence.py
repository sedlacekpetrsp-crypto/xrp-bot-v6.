"""K11 data-only PIT evidence diagnostic; no market prices or performance.

Archive observations are explicit timestamp/title-presence pairs. This helper does
not assert an article's original publication time: it only checks the frozen
24-hour Wayback corroboration rule in K11 PROTOCOL.md §3.
"""
from datetime import datetime, timedelta, timezone

WINDOW = timedelta(hours=24)


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc)


def classify_archive_evidence(release_at, observations):
    """Return (status, evidence), fail closed on invalid/contradictory archives.

    Each observation is (capture_datetime, title_present_bool). A title observed
    earlier than release-24h contradicts the CMS timestamp; a positive capture
    in [release, release+24h] corroborates it. Absence of corroboration is
    unverified, not 'ok'. Duplicate capture timestamps with conflicting title
    observations are rejected.
    """
    release = _utc(release_at)
    seen = {}
    for captured_at, present in observations:
        capture = _utc(captured_at)
        if type(present) is not bool:
            raise ValueError("title presence must be explicit boolean")
        if capture in seen and seen[capture] != present:
            raise ValueError("conflicting observations at same capture")
        seen[capture] = present
    early = sorted(t for t, present in seen.items()
                   if present and t < release - WINDOW)
    corroborating = sorted(t for t, present in seen.items()
                           if present and release <= t <= release + WINDOW)
    evidence = {
        "observations": len(seen),
        "earliest_contradiction_utc": early[0].isoformat() if early else None,
        "first_corroboration_utc": corroborating[0].isoformat() if corroborating else None,
    }
    if early:
        return "contradicted", evidence
    if corroborating:
        return "ok", evidence
    return "unverified", evidence
