"""K11 data-only step-0 gate; never computes returns."""
from datetime import datetime, timezone

# PROTOCOL.md §3.1: announcement window 2020-01-01 .. 2026-10-31 (inclusive), UTC.
WINDOW_START = datetime(2020, 1, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 11, 1, tzinfo=timezone.utc)  # exclusive
OOS_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
PIT_STATUSES = {"ok", "unverified", "contradicted"}


def _canonical(value, name):
    """Identity must already be canonical (stripped, upper-case token); never silently normalised."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing article/token identity")
    if value != value.strip():
        raise ValueError("non-canonical " + name + " (whitespace)")
    if name == "token" and value != value.upper():
        raise ValueError("non-canonical token (case)")
    return value

def audit_gate(events):
    seen, eligible, spot = set(), [], []
    article_instant = {}  # one CMS article = one announcement instant (dialog 0406)
    for e in events:
        if not isinstance(e, dict):
            raise ValueError("event must be mapping")
        article = _canonical(e.get("article_id"), "article_id")
        token = _canonical(e.get("token"), "token")
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
        dt = dt.astimezone(timezone.utc)
        if not (WINDOW_START <= dt < WINDOW_END):
            raise ValueError("announcement outside protocol window")
        if article_instant.setdefault(article, dt) != dt:
            raise ValueError("inconsistent announced_at for article " + article)
        spot.append(e)
        for field in ("pit_ok", "perp_ok", "coverage_ok"):
            if type(e.get(field)) is not bool:
                raise ValueError("missing or non-boolean gate: " + field)
        status = e.get("pit_status", "ok" if e["pit_ok"] else "unverified")
        if status not in PIT_STATUSES or (status == "ok") != e["pit_ok"]:
            raise ValueError("pit_status inconsistent with pit_ok")
        e = dict(e, pit_status=status)
        spot[-1] = e
        if e["pit_ok"] and e["perp_ok"] and e["coverage_ok"]:
            eligible.append((article, dt))
    n = len(eligible)
    independent = len({article for article, _ in eligible})
    oos = sum(dt >= OOS_START for _, dt in eligible)
    unverified = sum(not e["pit_ok"] for e in spot)
    ratio = unverified / len(spot) if spot else 1.0
    return {"eligible_events": n, "independent_articles": independent,
            "oos_events": oos, "spot_events": len(spot),
            "pit_unverified_ratio": ratio,
            "pit_unverified": sum(e["pit_status"] == "unverified" for e in spot),
            "pit_contradicted": sum(e["pit_status"] == "contradicted" for e in spot),
            "verdict": "DATA_GO" if n >= 60 and independent >= 25 and oos >= 20 and ratio <= 0.30 else "DATA_NO_GO"}
