#!/usr/bin/env python3
"""
Collect public posts from https://t.me/s/BlueWhaleCryptoTrading by paging backwards.

Goal: build a reproducible sample of ACTUAL public BTC trade posts. We keep:
- message id / timestamp / text
- attached photo URL if present
- candidate classification for signal, hold/update, result

No trading claim is scored here; this collector only gathers source material.
"""
from __future__ import annotations
import json, re, time, urllib.request, urllib.parse
from html import unescape
from pathlib import Path

BASE = "https://t.me/s/BlueWhaleCryptoTrading"
UA = "Mozilla/5.0 (compatible; BlueWhalePublicAudit/1.0)"
MAX_PAGES = 20
OUT = Path("blue_whale_public_posts.json")

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def clean_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s+", "\n", s)
    return s.strip()

def parse_page(html: str):
    # Split at message wrappers; each wrapper contains data-post="channel/id".
    chunks = re.split(r'(?=<div class="tgme_widget_message_wrap)', html)
    posts = []
    for ch in chunks:
        m = re.search(r'data-post="BlueWhaleCryptoTrading/(\d+)"', ch)
        if not m:
            continue
        mid = int(m.group(1))
        dtm = re.search(r'<time[^>]+datetime="([^"]+)"', ch)
        textm = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', ch, flags=re.S)
        text = clean_html(textm.group(1)) if textm else ""
        # Telegram public preview commonly stores photo URL in background-image:url('...')
        imgs = re.findall(r"background-image:url\('([^']+)'\)", ch)
        # Also capture video/image preview links if present.
        posts.append({
            "message_id": mid,
            "datetime": dtm.group(1) if dtm else None,
            "text": text,
            "image_urls": list(dict.fromkeys(imgs)),
        })
    return posts

def classify(text: str) -> list[str]:
    u = text.upper()
    tags = []
    if "$BTC" in u or "BTC" in u:
        tags.append("BTC")
    if re.search(r"\bSL\s*[:=]", u) or "STOP LOSS" in u or "STOPLOSS" in u:
        tags.append("HAS_SL_TEXT")
    if re.search(r"\bTP\s*[:=]", u) or "TAKE PROFIT" in u:
        tags.append("HAS_TP_TEXT")
    if any(x in u for x in ["LONG", "SHORT", "OPEN", "ENTRY", "BUY", "SELL"]):
        tags.append("TRADE_LIKE")
    if any(x in u for x in ["HOLDING", "STILL HOLD", "UPDATE"]):
        tags.append("UPDATE")
    if any(x in u for x in ["RESULT", "PROFIT", "TP HIT", "SL HIT", "STOP LOSS HIT"]):
        tags.append("RESULT_LIKE")
    return tags

def main():
    seen = {}
    before = None
    for page in range(MAX_PAGES):
        url = BASE if before is None else BASE + "?" + urllib.parse.urlencode({"before": before})
        html = fetch(url)
        posts = parse_page(html)
        if not posts:
            print(f"STOP no posts page={page} url={url}", flush=True)
            break
        for p in posts:
            p["tags"] = classify(p["text"])
            seen[p["message_id"]] = p
        oldest = min(p["message_id"] for p in posts)
        print(f"page={page+1} count={len(posts)} oldest={oldest} newest={max(p['message_id'] for p in posts)}", flush=True)
        if before is not None and oldest >= before:
            print("STOP pagination did not move", flush=True)
            break
        before = oldest
        time.sleep(0.25)

    posts = [seen[k] for k in sorted(seen)]
    OUT.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")
    candidates = [p for p in posts if "BTC" in p["tags"]]
    signalish = [p for p in candidates if "HAS_SL_TEXT" in p["tags"] or "HAS_TP_TEXT" in p["tags"] or "TRADE_LIKE" in p["tags"]]
    summary = {
        "posts_collected": len(posts),
        "btc_posts": len(candidates),
        "btc_signalish_posts": len(signalish),
        "oldest_id": posts[0]["message_id"] if posts else None,
        "newest_id": posts[-1]["message_id"] if posts else None,
        "candidate_preview": signalish[-30:],
    }
    print("RESULT_JSON=" + json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
