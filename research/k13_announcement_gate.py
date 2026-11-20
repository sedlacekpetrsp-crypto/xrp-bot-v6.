"""K13 data-only feasibility gate. No price series, trading or performance evaluation."""
import hashlib
import re
from datetime import datetime, timezone, timedelta

TITLE = re.compile(r"\b(?:leverage|margin)\b.*\b(?:tier|tiers|bracket|brackets)\b", re.I)
SYMBOL = re.compile(r"\b[A-Z0-9]{2,20}USDT\b")
TIER = re.compile(r"\b(?:tier|bracket)\s*#?\s*\d+\b", re.I)
NUMBER = re.compile(r"\b\d+(?:\.\d+)?\s*%?\b")

def utc(value):
    if not isinstance(value, str):
        raise ValueError("timestamp_not_string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("naive_timestamp")
    return dt.astimezone(timezone.utc)

def article_gate(article):
    """Fail closed: independently captured 200 response within 24h after release."""
    if not isinstance(article, dict):
        return {"ok": False, "reason": "bad_record"}
    required = ("code", "title", "release_at", "capture_at", "status", "text", "effective_at")
    if any(k not in article for k in required):
        return {"ok": False, "reason": "missing_field"}
    try:
        release, capture, effective = (utc(article[k]) for k in ("release_at", "capture_at", "effective_at"))
    except (ValueError, TypeError, OverflowError):
        return {"ok": False, "reason": "bad_timestamp"}
    if not all(isinstance(article[k], str) for k in ("code", "title", "text")):
        return {"ok": False, "reason": "bad_text"}
    if not TITLE.search(article["title"]):
        return {"ok": False, "reason": "not_target"}
    if article["status"] != 200:
        return {"ok": False, "reason": "http_status"}
    if not release <= capture <= release + timedelta(hours=24):
        return {"ok": False, "reason": "capture_outside_window"}
    if effective < release:
        return {"ok": False, "reason": "effective_before_release"}
    if not (SYMBOL.search(article["text"]) and TIER.search(article["text"]) and NUMBER.search(article["text"])):
        return {"ok": False, "reason": "missing_tier_evidence"}
    return {"ok": True, "reason": "pit_evidence_only"}

def feasibility(articles):
    """Freeze deterministic first 20 unique article codes; never interpret symbol count as event count."""
    if not isinstance(articles, list):
        raise ValueError("articles_must_be_list")
    by_code = {}
    for article in articles:
        if not isinstance(article, dict) or not isinstance(article.get("code"), str) or not article["code"]:
            raise ValueError("invalid_code")
        code = article["code"]
        if code in by_code and article != by_code[code]:
            raise ValueError("conflicting_duplicate_code")
        by_code[code] = article
    selected = sorted(by_code.values(), key=lambda a: (hashlib.sha256(a["code"].encode()).hexdigest(), a["code"]))[:20]
    outcomes = [article_gate(a) for a in selected]
    # A preliminary sample cannot prove population coverage; no GO before >=20 observations.
    return {"sample_size": len(selected), "pit_ok": sum(o["ok"] for o in outcomes),
            "status": "DATA_FEASIBLE_SAMPLE" if len(selected) == 20 and sum(o["ok"] for o in outcomes) >= 10 else "DATA_NO_GO",
            "performance_authorized": False}
