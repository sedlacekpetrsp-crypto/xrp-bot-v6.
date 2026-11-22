"""K11 pre-performance event eligibility census. Data-only, fail closed.

Inputs are externally verified evidence records; this module does not verify
Wayback authenticity or fetch market data. No price or return fields accepted.
"""
from collections import Counter
from datetime import datetime, timezone
from typing import Mapping


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def audit_events(events, *, min_events=60, min_articles=25,
                 min_recent=20, max_unverified_fraction=0.30):
    """Census distinct eligible events and independent source articles.

    Eligibility: unique event ID, verified PIT capture strictly before
    decision, perpetual tradable at decision, minute-bar coverage >= 95%.
    An unverified event remains in denominator (never silently dropped).
    """
    if not isinstance(events, list):
        raise ValueError("events must be list")
    ids = set()
    articles = set()
    counts = Counter()
    eligible = 0
    recent = 0
    unverified = 0
    for item in events:
        if not isinstance(item, Mapping):
            raise ValueError("event must be mapping")
        if set(item) != {"event_id", "article_id", "announcement_at",
                         "capture_at", "decision_at", "perp_tradable",
                         "coverage_fraction"}:
            raise ValueError("unexpected/missing fields")
        eid, article = item["event_id"], item["article_id"]
        if not isinstance(eid, str) or not eid.strip() or eid in ids:
            raise ValueError("invalid or duplicate event_id")
        ids.add(eid)
        if not isinstance(article, str) or not article.strip():
            raise ValueError("invalid article_id")
        announcement = _utc(item["announcement_at"])
        decision = _utc(item["decision_at"])
        capture = None if item["capture_at"] is None else _utc(item["capture_at"])
        if decision <= announcement:
            raise ValueError("decision must follow announcement")
        if type(item["perp_tradable"]) is not bool:
            raise ValueError("perp_tradable must be bool")
        coverage = item["coverage_fraction"]
        if type(coverage) not in (int, float) or not 0 <= coverage <= 1:
            raise ValueError("coverage must be finite fraction")
        pit = capture is not None and announcement <= capture < decision
        if not pit:
            unverified += 1
            counts["pit_unverified"] += 1
        if not item["perp_tradable"]:
            counts["perp_unavailable"] += 1
        if coverage < 0.95:
            counts["coverage_below_95pct"] += 1
        if pit and item["perp_tradable"] and coverage >= 0.95:
            eligible += 1
            articles.add(article)
            if announcement >= datetime(2025, 1, 1, tzinfo=timezone.utc):
                recent += 1
    fraction = unverified / len(events) if events else 1.0
    checks = {
        "eligible_events": eligible >= min_events,
        "independent_articles": len(articles) >= min_articles,
        "recent_events": recent >= min_recent,
        "pit_unverified_fraction": fraction <= max_unverified_fraction,
    }
    return {"verdict": "DATA_GO_PRELIMINARY" if all(checks.values()) else "DATA_NO_GO",
            "checks": checks, "total_events": len(events),
            "eligible_events": eligible, "independent_articles": len(articles),
            "recent_events": recent, "pit_unverified": unverified,
            "pit_unverified_fraction": fraction, "exclusion_reasons": dict(counts),
            "warning": "Evidence authenticity and source independence require separate review; no performance approval."}
