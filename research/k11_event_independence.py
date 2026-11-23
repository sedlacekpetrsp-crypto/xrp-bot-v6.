"""Conservative PIT event-independence preflight for K11; no prices or returns."""
from datetime import datetime, timezone

def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc)

def audit_independence(events, *, as_of, min_articles=25):
    """Events: article_id, asset, announced_at, observed_at; fail closed."""
    cutoff = _utc(as_of)
    if not isinstance(min_articles, int) or isinstance(min_articles, bool) or min_articles < 1:
        raise ValueError("invalid minimum")
    seen = set()
    articles = set()
    rejected = []
    accepted = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("invalid event")
        article = event.get("article_id")
        asset = event.get("asset")
        if not isinstance(article, str) or not article.strip() or not isinstance(asset, str) or not asset.strip():
            raise ValueError("missing article/asset identity")
        announcement = _utc(event.get("announced_at"))
        observed = _utc(event.get("observed_at"))
        if announcement > observed or observed > cutoff:
            rejected.append(index)
            continue
        key = (article.strip().casefold(), asset.strip().upper())
        if key in seen:
            rejected.append(index)
            continue
        seen.add(key)
        articles.add(article.strip().casefold())
        accepted.append(index)
    return {"accepted_indices": accepted, "rejected_indices": rejected,
            "independent_articles": len(articles),
            "article_gate_ok": len(articles) >= min_articles}
