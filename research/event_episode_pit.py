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

    Fail closed on duplicate IDs, conflicting source publication times, malformed
    times, or nonpositive embargo. Source identity connects symbols; same-symbol
    publication adjacency connects events transitively.
    """
    if isinstance(embargo_minutes, bool) or not isinstance(embargo_minutes, int) or embargo_minutes <= 0:
        raise ValueError("embargo_minutes must be positive integer")
    records = list(events)
    seen = set()
    valid = []
    excluded = []
    source_times = {}
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
        prior = source_times.setdefault(event.source_id, published)
        if abs((published - prior).total_seconds()) > 60:
            raise ValueError('source_id publication collision')
        if published > decision or received > decision:
            excluded.append({"event_id": event.event_id, "reason": "not_point_in_time"})
        elif received < published:
            excluded.append({"event_id": event.event_id, "reason": "receipt_before_publication"})
        else:
            valid.append((event, published, received, decision))
    valid.sort(key=lambda x: (x[1], x[0].symbol, x[0].event_id))
    parent = list(range(len(valid)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i, j):
        a, b = root(i), root(j)
        if a != b:
            parent[max(a, b)] = min(a, b)
    last_symbol, source_first = {}, {}
    window = timedelta(minutes=embargo_minutes)
    for i, (event, published, received, decision) in enumerate(valid):
        if event.source_id in source_first:
            union(i, source_first[event.source_id])
        else:
            source_first[event.source_id] = i
        previous = last_symbol.get(event.symbol)
        if previous is not None and published - valid[previous][1] <= window:
            union(i, previous)
        last_symbol[event.symbol] = i
    groups = {}
    for i, row in enumerate(valid):
        groups.setdefault(root(i), []).append(row)
    episodes = []
    for members in groups.values():
        symbols = tuple(sorted({e.symbol for e, _, _, _ in members}))
        pubs = [p for _, p, _, _ in members]
        decisions = [d for _, _, _, d in members]
        episodes.append({
            "symbol": symbols[0] if len(symbols) == 1 else None,
            "symbols": symbols,
            "first_decision": min(decisions).isoformat(),
            "last_decision": max(decisions).isoformat(),
            "first_publication": min(pubs).isoformat(),
            "last_publication": max(pubs).isoformat(),
            "max_episode_span_minutes": (max(pubs) - min(pubs)).total_seconds() / 60,
            "event_ids": tuple(sorted(e.event_id for e, _, _, _ in members)),
            "source_count": len({e.source_id for e, _, _, _ in members}),
        })
    episodes.sort(key=lambda g: (g["first_publication"], g["event_ids"]))
    per_symbol = {symbol: sum(symbol in ep["symbols"] for ep in episodes)
                  for symbol in sorted({e.symbol for e, _, _, _ in valid})}
    return {
        "episodes": episodes,
        "excluded": sorted(excluded, key=lambda x: x["event_id"]),
        "eligible_events": len(valid),
        "independent_episodes": len(episodes),
        "per_symbol_episodes": per_symbol,
        "max_episode_span_minutes": max((e["max_episode_span_minutes"] for e in episodes), default=0),
    }
