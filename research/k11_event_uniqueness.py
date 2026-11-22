"""K11 data-only audit: prevent duplicate announcements inflating event counts.

No market prices, trading decisions or performance evaluation.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO8601 string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("naive timestamp")
    return dt.astimezone(timezone.utc)


def _url(value):
    if not isinstance(value, str):
        raise ValueError("invalid URL")
    parts = urlsplit(value.strip())
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise ValueError("source must be HTTPS without credentials")
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/") or "/", "", ""))


def audit_event_uniqueness(records):
    """Fail closed on duplicate CMS ids, conflicting URLs and repeated event keys.

    A repeated (asset, delisting effective UTC time) across articles counts once.
    Duplicates are flagged, never silently counted as independent events.
    """
    seen_ids, seen_urls, seen_events = set(), set(), set()
    accepted, rejected = [], []
    for index, record in enumerate(records):
        try:
            if not isinstance(record, dict):
                raise ValueError("record must be mapping")
            cms_id = record["cms_id"]
            asset = record["asset"]
            if isinstance(cms_id, bool) or not isinstance(cms_id, (str, int)) or not str(cms_id).strip():
                raise ValueError("invalid cms_id")
            if not isinstance(asset, str) or not asset.strip():
                raise ValueError("invalid asset")
            url = _url(record["source_url"])
            published = _utc(record["published_at"])
            effective = _utc(record["effective_at"])
            if published >= effective:
                raise ValueError("publication not before effective time")
            event = (asset.strip().upper(), effective)
            if str(cms_id) in seen_ids or url in seen_urls or event in seen_events:
                raise ValueError("duplicate event or source")
            seen_ids.add(str(cms_id))
            seen_urls.add(url)
            seen_events.add(event)
            accepted.append(index)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    return {"accepted_indices": accepted, "rejected": rejected, "unique_events": len(accepted)}
