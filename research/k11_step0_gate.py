"""K11 data-only step-0 gate; never computes returns."""
from datetime import datetime, timezone

def audit_gate(events):
    seen, eligible, spot = set(), [], []
    for e in events:
        if not isinstance(e, dict):
            raise ValueError("event must be mapping")
        article, token = e.get("article_id"), e.get("token")
        if not isinstance(article, str) or not article.strip() or not isinstance(token, str) or not token.strip():
            raise ValueError("missing article/token identity")
        key = (article, token)
        if key in seen:
            raise ValueError("duplicate article/token event")
        seen.add(key)
        if e.get("event_type") != "spot_delist":
            continue
        stamp = e.get("announced_at")
        if not isinstance(stamp, str):
            raise ValueError("missing timestamp")
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid timestamp") from exc
        if dt.tzinfo is None:
            raise ValueError("timestamp requires timezone")
        spot.append(e)
        for field in ("pit_ok", "perp_ok", "coverage_ok"):
            if type(e.get(field)) is not bool:
                raise ValueError("missing or non-boolean gate: " + field)
        if e["pit_ok"] and e["perp_ok"] and e["coverage_ok"]:
            eligible.append((article, dt.astimezone(timezone.utc)))
    n = len(eligible)
    independent = len({article for article, _ in eligible})
    oos = sum(dt >= datetime(2025, 1, 1, tzinfo=timezone.utc) for _, dt in eligible)
    unverified = sum(not e["pit_ok"] for e in spot)
    ratio = unverified / len(spot) if spot else 1.0
    return {"eligible_events": n, "independent_articles": independent,
            "oos_events": oos, "spot_events": len(spot),
            "pit_unverified_ratio": ratio,
            "verdict": "DATA_GO" if n >= 60 and independent >= 25 and oos >= 20 and ratio <= 0.30 else "DATA_NO_GO"}
