"""XRP news from independent RSS feeds; failures never block the trading loop."""
import asyncio
import copy
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

BUILD = "xrp-news-v6-rss-20260923"
FEEDS = {
    "coindesk.com": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph.com": "https://cointelegraph.com/rss",
    "decrypt.co": "https://decrypt.co/feed",
}
CACHE_SECONDS = 300
MAX_AGE_SECONDS = 7200
FAILURE_BACKOFF_SECONDS = 900
MAX_BACKOFF_SECONDS = 21600
MAX_FEED_BYTES = 2000000

POSITIVE = {
    "etf approved": 5, "approves xrp": 5, "approval": 2, "approved": 3,
    "sec drops": 5, "sec dismisses": 5, "appeal dismissed": 5,
    "lawsuit dismissed": 5, "legal victory": 4, "wins lawsuit": 4,
    "license granted": 4, "wins license": 4, "regulatory approval": 4,
    "partnership": 2, "partners with": 2, "adoption": 2, "adopts xrp": 3,
    "integrates xrp": 3, "launches xrp": 2, "xrp launch": 2,
    "institutional": 1, "expands": 1, "record inflows": 4, "inflows": 2,
    "listing": 2, "lists xrp": 3,
}
NEGATIVE = {
    "etf rejected": -5, "rejects xrp": -5, "rejection": -3,
    "sec sues": -5, "lawsuit": -2, "investigation": -3, "probe": -2,
    "charged": -4, "charges": -4, "ban": -4, "bans": -4,
    "delist": -4, "delisting": -4, "hack": -5, "hacked": -5,
    "exploit": -5, "outage": -3, "breach": -4, "fraud": -4,
    "scam": -4, "liquidation": -2, "selloff": -3,
}


def _neutral():
    return dict(build=BUILD, status="starting", bullish=False, bearish=False,
                score=0, positive_count=0, negative_count=0, sources=0,
                headlines=[], checked_at=None, last_success_at=None,
                next_retry_at=None, failure_count=0, error=None,
                upstream_error=None, providers={})


_cache = {"ts": 0.0, "data": _neutral(), "items": []}
_provider_state = {}
_refresh_task = None


def _headline_score(title):
    title = re.sub(r"\s+", " ", title.lower()).strip()
    # Predictions, questions and negated claims are not confirmed events.
    if re.search(r"\b(could|might|may|rumou?r|predict\w*|forecast\w*|if|not|denies|denied)\b|\?", title):
        return 0, []
    matches = []
    for phrase, value in sorted({**POSITIVE, **NEGATIVE}.items(), key=lambda p: -len(p[0])):
        for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", title):
            if not any(match.start() < b and match.end() > a for a, b, _, _ in matches):
                matches.append((match.start(), match.end(), phrase, value))
    return max(-6, min(6, sum(m[3] for m in matches))), [m[2] for m in matches]


def _parse_seen(value):
    if not value:
        return None
    try:
        date = parsedate_to_datetime(value)
    except (ValueError, TypeError, OverflowError):
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return date.astimezone(timezone.utc) if date.tzinfo else None


def _parse_feed(body, source):
    if len(body) > MAX_FEED_BYTES or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("RSS size or entity declaration rejected")
    root = ET.fromstring(body)
    if root.tag != "rss":
        raise ValueError("Expected RSS document")
    items = []
    now = datetime.now(timezone.utc)
    for row in root.findall("./channel/item")[:100]:
        title = re.sub(r"<[^>]*>", "", row.findtext("title") or "").strip()
        if not re.search(r"\b(XRP|Ripple|XRPL)\b", title, re.I):
            continue
        date = _parse_seen(row.findtext("pubDate"))
        if date is None or not 0 <= (now - date).total_seconds() <= MAX_AGE_SECONDS:
            continue
        url = (row.findtext("link") or "").strip()
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host == source or host.endswith("." + source)):
            continue
        score, hits = _headline_score(title)
        items.append(dict(title=title, source=source, url=url, seen_at=date.isoformat(),
                          score=score, hits=hits))
    return items


def _summarize(items):
    now = datetime.now(timezone.utc)
    fresh, seen = [], set()
    for item in items:
        date = _parse_seen(item.get("seen_at"))
        if date is None or not 0 <= (now - date).total_seconds() <= MAX_AGE_SECONDS:
            continue
        key = re.sub(r"\W+", " ", item["title"].lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        fresh.append(dict(item, age_min=(now - date).total_seconds() / 60))
    positive = [x for x in fresh if x["score"] >= 2]
    negative = [x for x in fresh if x["score"] <= -2]
    sources = {x["source"] for x in positive}
    total = sum(x["score"] for x in fresh)
    return dict(
        bullish=bool(not negative and total >= 4 and
                     (max((x["score"] for x in positive), default=0) >= 4 or len(sources) >= 2)),
        bearish=bool(negative and sum(x["score"] for x in negative) <= -4),
        score=total, positive_count=len(positive), negative_count=len(negative),
        sources=len(sources),
        headlines=sorted(fresh, key=lambda x: (-abs(x["score"]), x["age_min"]))[:6],
    )


def _retry_delay(response, failures):
    delay = min(MAX_BACKOFF_SECONDS, FAILURE_BACKOFF_SECONDS * 2 ** min(failures - 1, 4))
    if response is not None and response.status_code == 429:
        raw = response.headers.get("Retry-After", "")
        try:
            requested = float(raw)
        except ValueError:
            date = _parse_seen(raw)
            requested = (date - datetime.now(timezone.utc)).total_seconds() if date else 0
        delay = max(delay, requested)
    return max(0, delay)


async def _fetch_source(client, source, url):
    state = _provider_state.setdefault(source, {"retry_at": 0, "failures": 0})
    if time.monotonic() < state["retry_at"]:
        return []
    try:
        async def read():
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_FEED_BYTES:
                        raise ValueError("RSS too large")
                return _parse_feed(bytes(body), source)
        items = await asyncio.wait_for(read(), timeout=20)
        state.update(status="ok", failures=0, retry_at=0, next_retry_at=None,
                     last_success_at=datetime.now(timezone.utc).isoformat(), error=None,
                     matching_articles=len(items))
        return items
    except Exception as exc:
        failures = state["failures"] + 1
        response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
        delay = _retry_delay(response, failures)
        state.update(status="backoff", failures=failures, retry_at=time.monotonic() + delay,
                     next_retry_at=datetime.fromtimestamp(time.time() + delay, timezone.utc).isoformat(),
                     error=f"{type(exc).__name__}: {exc}")
        return []


async def _refresh():
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "xrp-paper-bot-news-monitor/2.0"}) as client:
            results = await asyncio.gather(*(_fetch_source(client, s, u) for s, u in FEEDS.items()))
        now = datetime.now(timezone.utc).isoformat()
        providers = {s: {k: v for k, v in state.items() if k != "retry_at"}
                     for s, state in _provider_state.items()}
        successful = [s for s, p in providers.items() if p.get("status") == "ok"]
        items = [item for group in results for item in group]
        # Only successful current fetches may contribute trading signals.
        _cache["items"] = items
        data = _neutral()
        data.update(_summarize(items), checked_at=now, providers=providers,
                    status="running" if successful else "degraded",
                    partial=len(successful) < len(FEEDS), active_sources=len(successful),
                    last_success_at=now if successful else _cache["data"].get("last_success_at"),
                    failure_count=sum(p.get("failures", 0) for p in providers.values()),
                    next_retry_at=min((p["next_retry_at"] for p in providers.values()
                                       if p.get("next_retry_at")), default=None),
                    upstream_error=None if successful else "All RSS sources unavailable",
                    note="RSS XRP/Ripple headlines; price confirmation remains required.")
        _cache["data"] = data
        print(f"NEWS_FEED status={data['status']} active_sources={len(successful)} score={data['score']}", flush=True)
    except Exception as exc:
        _cache["items"] = []
        _cache["data"].update(_summarize([]), status="degraded", upstream_error=type(exc).__name__)
    finally:
        _cache["ts"] = time.monotonic()


async def get_xrp_news(force=False):
    global _refresh_task
    if force or not _cache["ts"] or time.monotonic() - _cache["ts"] >= CACHE_SECONDS:
        if _refresh_task is None or _refresh_task.done():
            _refresh_task = asyncio.create_task(_refresh())
    # Network work runs separately: no timeout can hold up stop-loss evaluation.
    return cached_state()


def cached_state():
    data = copy.deepcopy(_cache["data"])
    data.update(_summarize(_cache["items"]))
    if _cache["ts"] and time.monotonic() - _cache["ts"] > CACHE_SECONDS + 30:
        data.update(_summarize([]), status="stale")
    return data
