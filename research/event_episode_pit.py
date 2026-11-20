"""PAPER research: deterministic event-episode PIT/independence gate.

Not a trading signal or a performance estimator. Events are grouped only if their
publicly available timestamps are within the frozen embargo window. A source
published after the decision cannot enter the eligible sample.
"""
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Event:
    event_id: str
    symbol: str
    published_at: datetime
    received_at: datetime
    decision_at: datetime
    source_id: str


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc)


def audit_episodes(events: Iterable[Event], embargo_minutes: int = 1440) -> dict:
    """Return eligible independent episodes and explicit exclusions.

    Fail closed on duplicate IDs, source collisions, malformed times, or
    nonpositive embargo. Identical source IDs across events are clustered only
    within a symbol; no claim of cross-symbol statistical independence.
    """
    if isinstance(embargo_minutes, bool) or not isinstance(embargo_minutes, int) or embargo_minutes <= 0:
        raise ValueError("embargo_minutes must be positive integer")
    records = list(events)
    seen = set()
    valid = []
    excluded = []
    for event in records:
        if not isinstance(event, Event) or not all(
            isinstance(x, str) and x.strip()
            for x in (event.event_id, event.symbol, event.source_id)
        ):
            raise ValueError("invalid event record")
        if event.event_id in seen:
            raise ValueError("duplicate event_id")
        seen.add(event.event_id)
        published, received, decision = map(
            _utc, (event.published_at, event.received_at, event.decision_at)
        )
        if published > decision or received > decision:
            excluded.append({"event_id": event.event_id, "reason": "not_point_in_time"})
        elif received < published:
            excluded.append({"event_id": event.event_id, "reason": "receipt_before_publication"})
        else:
            valid.append((event, published, received, decision))
    valid.sort(key=lambda x: (x[3], x[0].symbol, x[0].event_id))
    by_symbol = {}
    episodes = []
    window = timedelta(minutes=embargo_minutes)
    for event, published, received, decision in valid:
        group = by_symbol.setdefault(event.symbol, [])
        # Cluster transitively by decision time, preventing event-count inflation.
        matches = [g for g in group if decision - g["last_decision"] <= window]
        if matches:
            episode = matches[-1]
            episode["last_decision"] = decision
            episode["event_ids"].append(event.event_id)
            episode["source_ids"].add(event.source_id)
        else:
            episode = {"symbol": event.symbol, "first_decision": decision,
                       "last_decision": decision, "event_ids": [event.event_id],
                       "source_ids": {event.source_id}}
            group.append(episode)
            episodes.append(episode)
    return {
        "episodes": [
            {"symbol": g["symbol"], "first_decision": g["first_decision"].isoformat(),
             "last_decision": g["last_decision"].isoformat(),
             "event_ids": tuple(g["event_ids"]), "source_count": len(g["source_ids"])}
            for g in episodes
        ],
        "excluded": sorted(excluded, key=lambda x: x["event_id"]),
        "eligible_events": len(valid),
        "independent_episodes": len(episodes),
    }
