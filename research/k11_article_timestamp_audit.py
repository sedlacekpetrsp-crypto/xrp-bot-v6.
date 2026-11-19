"""K11 pre-performance article-cluster timestamp integrity audit (synthetic/data only)."""
from datetime import datetime, timezone


def audit_article_timestamps(events):
    """Reject inconsistent announcement timestamps for tokens in the same CMS article.

    Each article_id is one announcement cluster. Timestamp equality is UTC instant
    equality (different explicit offsets may represent the same instant).
    No returns, prices, or market data are read.
    """
    by_article = {}
    count = 0
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("event must be a mapping")
        article = event.get("article_id")
        stamp = event.get("announced_at")
        if not isinstance(article, str) or not article or article != article.strip():
            raise ValueError("invalid article_id")
        if not isinstance(stamp, str):
            raise ValueError("missing announced_at")
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid announced_at") from exc
        if dt.tzinfo is None:
            raise ValueError("naive announced_at")
        instant = dt.astimezone(timezone.utc)
        if article in by_article and by_article[article] != instant:
            raise ValueError("inconsistent announced_at for article " + article)
        by_article[article] = instant
        count += 1
    return {"events": count, "articles": len(by_article), "consistent": True}
