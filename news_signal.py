import asyncio
import re
import time
from datetime import datetime, timezone

import httpx

BUILD = "xrp-news-v5-disable-gdelt-20260923"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_ENABLED = False  # upstream repeatedly returns HTTP 429; keep news neutral instead of erroring
CACHE_SECONDS = 21600
FAILURE_BACKOFF_SECONDS = 21600
MAX_BACKOFF_SECONDS = 21600
LOOKBACK = "2h"
MAX_RECORDS = 30

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

_cache = {
    "ts": 0.0,
    "data": {
        "build": BUILD,
        "status": "starting",
        "bullish": False,
        "bearish": False,
        "score": 0,
        "positive_count": 0,
        "negative_count": 0,
        "sources": 0,
        "headlines": [],
        "checked_at": None,
        "last_success_at": None,
        "next_retry_at": None,
        "failure_count": 0,
        "error": None,
    },
}
_lock = asyncio.Lock()
_failure_count = 0
_retry_not_before = 0.0


def _headline_score(title):
    t = re.sub(r"\s+", " ", (title or "").lower()).strip()
    score = 0
    hits = []
    for phrase, value in POSITIVE.items():
        if phrase in t:
            score += value
            hits.append(phrase)
    for phrase, value in NEGATIVE.items():
        if phrase in t:
            score += value
            hits.append(phrase)
    return max(-6, min(6, score)), hits


def _parse_seen(value):
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _fetch():
    params = {
        "query": '(XRP OR Ripple) sourcelang:english',
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(MAX_RECORDS),
        "timespan": LOOKBACK,
        "sort": "datedesc",
    }
    headers = {"User-Agent": "xrp-paper-bot-news-monitor/1.0"}
    timeout = httpx.Timeout(20.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r = await client.get(GDELT_URL, params=params)
        r.raise_for_status()
        payload = r.json()
    rows = payload.get("articles") or payload.get("results") or []
    now = datetime.now(timezone.utc)
    items = []
    seen_titles = set()
    for row in rows:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        key = re.sub(r"\W+", " ", title.lower()).strip()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        score, hits = _headline_score(title)
        seen = _parse_seen(row.get("seendate") or row.get("date") or row.get("published"))
        age_min = None
        if seen:
            age_min = max(0.0, (now - seen).total_seconds() / 60.0)
            if age_min > 130:
                continue
        source = str(row.get("domain") or row.get("source") or "").strip()
        items.append({
            "title": title,
            "source": source,
            "url": row.get("url"),
            "seen_at": seen.isoformat() if seen else None,
            "age_min": age_min,
            "score": score,
            "hits": hits,
        })

    scored = [x for x in items if x["score"] != 0]
    positive = [x for x in scored if x["score"] >= 2]
    negative = [x for x in scored if x["score"] <= -2]
    sources = {x["source"] for x in positive if x["source"]}
    total = sum(x["score"] for x in scored)
    strongest = max([x["score"] for x in positive], default=0)

    bullish = (
        not negative
        and total >= 4
        and (strongest >= 4 or len(sources) >= 2)
    )
    bearish = bool(negative) and sum(x["score"] for x in negative) <= -4

    ranked = sorted(
        items,
        key=lambda x: (abs(x["score"]), -(x["age_min"] if x["age_min"] is not None else 9999)),
        reverse=True,
    )[:6]
    return {
        "build": BUILD,
        "status": "running",
        "bullish": bullish,
        "bearish": bearish,
        "score": total,
        "positive_count": len(positive),
        "negative_count": len(negative),
        "sources": len(sources),
        "headlines": ranked,
        "checked_at": now.isoformat(),
        "error": None,
    }


async def get_xrp_news(force=False):
    global _failure_count, _retry_not_before
    if not GDELT_ENABLED:
        now_iso = datetime.now(timezone.utc).isoformat()
        data = dict(_cache["data"])
        data.update({
            "build": BUILD,
            "status": "disabled",
            "bullish": False,
            "bearish": False,
            "score": 0,
            "positive_count": 0,
            "negative_count": 0,
            "sources": 0,
            "headlines": [],
            "checked_at": now_iso,
            "next_retry_at": None,
            "failure_count": 0,
            "error": None,
            "upstream_error": None,
            "note": "GDELT disabled after repeated HTTP 429; news filter is neutral and does not block trading.",
        })
        _cache["data"] = data
        _cache["ts"] = time.monotonic()
        return data
    now = time.monotonic()
    if not force and now < _retry_not_before:
        return _cache["data"]
    if not force and now - float(_cache["ts"]) < CACHE_SECONDS:
        return _cache["data"]
    async with _lock:
        now = time.monotonic()
        if not force and now < _retry_not_before:
            return _cache["data"]
        if not force and now - float(_cache["ts"]) < CACHE_SECONDS:
            return _cache["data"]
        try:
            data = await _fetch()
            _failure_count = 0
            _retry_not_before = 0.0
            data["last_success_at"] = data.get("checked_at")
            data["next_retry_at"] = None
            data["failure_count"] = 0
            _cache["data"] = data
            _cache["ts"] = now
            print(
                "NEWS_FEED status={} bullish={} bearish={} score={} positive={} negative={} sources={}".format(
                    data.get("status"), data.get("bullish"), data.get("bearish"),
                    data.get("score"), data.get("positive_count"),
                    data.get("negative_count"), data.get("sources")
                ),
                flush=True,
            )
        except Exception as e:
            _failure_count += 1
            delay = min(MAX_BACKOFF_SECONDS, FAILURE_BACKOFF_SECONDS * (2 ** min(_failure_count - 1, 3)))
            if isinstance(e, httpx.HTTPStatusError) and e.response is not None and e.response.status_code == 429:
                delay = MAX_BACKOFF_SECONDS
                raw = e.response.headers.get("Retry-After", "")
                try:
                    delay = max(delay, float(raw))
                except (TypeError, ValueError):
                    pass
            _retry_not_before = now + delay
            previous = dict(_cache["data"])
            previous["status"] = "degraded"
            upstream_error = f"{type(e).__name__}: {e}"
            previous["error"] = None
            previous["upstream_error"] = upstream_error
            previous["checked_at"] = datetime.now(timezone.utc).isoformat()
            previous["next_retry_at"] = datetime.fromtimestamp(time.time() + delay, timezone.utc).isoformat()
            previous["failure_count"] = _failure_count
            previous["bullish"] = False
            previous["bearish"] = False
            _cache["data"] = previous
            _cache["ts"] = now
            print(
                "NEWS_FEED_DEGRADED seconds={} failure={} upstream_error={}".format(
                    int(delay), _failure_count, upstream_error
                ),
                flush=True,
            )
        return _cache["data"]


def cached_state():
    return _cache["data"]
