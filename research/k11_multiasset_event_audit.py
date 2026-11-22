"""K11 data-only: distinguish multi-asset announcements from independent events.

A single CMS article may delist multiple assets. Article identity is not event
identity. This module does not assess returns or run historical performance.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


def _time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _source(value):
    if not isinstance(value, str):
        raise ValueError("URL must be string")
    p = urlsplit(value.strip())
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError("canonical HTTPS source required")
    return urlunsplit(("https", p.hostname.lower(), p.path.rstrip("/") or "/", "", ""))


def audit_multiasset_events(records):
    """Fail closed on identity conflicts; count unique asset/effective pairs.

    A CMS id can legitimately cover multiple assets, but it must resolve to
    exactly one canonical source URL. A URL cannot claim two CMS ids. Repeated
    asset/effective pairs are not independent events even across articles.
    """
    cms_to_url, url_to_cms, seen_events = {}, {}, set()
    accepted, rejected = [], []
    for i, row in enumerate(records):
        try:
            if not isinstance(row, dict):
                raise ValueError("record must be mapping")
            cms = row["cms_id"]
            asset = row["asset"]
            if isinstance(cms, bool) or not isinstance(cms, (str, int)) or not str(cms).strip():
                raise ValueError("invalid cms_id")
            if not isinstance(asset, str) or not asset.strip():
                raise ValueError("invalid asset")
            cms = str(cms).strip()
            asset = asset.strip().upper()
            url = _source(row["source_url"])
            publication = _time(row["published_at"])
            effective = _time(row["effective_at"])
            if publication >= effective:
                raise ValueError("announcement not available before effective time")
            if cms in cms_to_url and cms_to_url[cms] != url:
                raise ValueError("CMS id mapped to conflicting URLs")
            if url in url_to_cms and url_to_cms[url] != cms:
                raise ValueError("URL mapped to conflicting CMS ids")
            key = (asset, effective)
            if key in seen_events:
                raise ValueError("duplicate asset/effective event")
            cms_to_url[cms] = url
            url_to_cms[url] = cms
            seen_events.add(key)
            accepted.append(i)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            rejected.append({"index": i, "reason": str(exc)})
    return {"accepted_indices": accepted, "rejected": rejected,
            "unique_events": len(accepted), "unique_announcements": len(cms_to_url)}
