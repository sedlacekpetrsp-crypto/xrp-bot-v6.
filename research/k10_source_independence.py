"""K10 conservative historical publisher independence diagnostic; DATA ONLY.
Archive snapshots and mirrored pages are not independent publishers.
This is NOT proof of exchange ownership or authorization to backtest.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Evidence:
    address: str
    exchange: str
    publisher_id: str
    original_url: str
    observed_at: datetime
    decision_at: datetime

def _utc(t):
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return t.astimezone(timezone.utc)

def assess(evidence, min_independent=2):
    """Fail closed. publisher_id must be independently provenance-verified."""
    if min_independent < 2:
        raise ValueError("independent-source threshold must be >=2")
    if not evidence:
        return {"status":"DATA_NO_GO","reason":"no_evidence","publishers":0}
    pairs, publishers = set(), set()
    for e in evidence:
        if not e.address or not e.exchange or not e.publisher_id or not e.original_url:
            return {"status":"DATA_NO_GO","reason":"missing_provenance","publishers":0}
        url = urlsplit(e.original_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            return {"status":"DATA_NO_GO","reason":"invalid_original_url","publishers":0}
        if _utc(e.observed_at) > _utc(e.decision_at):
            return {"status":"DATA_NO_GO","reason":"future_evidence","publishers":0}
        pairs.add((e.address.strip(),e.exchange.strip().casefold()))
        publishers.add(e.publisher_id.strip().casefold())
    if len(pairs) != 1:
        return {"status":"DATA_NO_GO","reason":"conflicting_attribution","publishers":len(publishers)}
    if len(publishers) < min_independent:
        return {"status":"DATA_NO_GO","reason":"insufficient_independent_publishers","publishers":len(publishers)}
    return {"status":"PROVISIONAL_PIT_ONLY","reason":"publisher_count_only_not_truth","publishers":len(publishers)}
