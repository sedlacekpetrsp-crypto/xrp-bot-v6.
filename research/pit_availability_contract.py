"""Fail-closed point-in-time availability audit for research event feeds.

Diagnostic only: no trading signals, performance evaluation or network access.
An event is eligible only after BOTH publication and first observation.
"""
from datetime import datetime, timezone
from typing import Iterable, Mapping


class PITAvailabilityError(ValueError):
    """Event feed cannot be certified point-in-time."""


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise PITAvailabilityError(f"{field}: ISO timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PITAvailabilityError(f"{field}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PITAvailabilityError(f"{field}: timezone required")
    return parsed.astimezone(timezone.utc)


def audit_event_availability(
    events: Iterable[Mapping[str, str]], decision_at: str
) -> tuple[str, ...]:
    """Return eligible event IDs; reject any unverifiable or future-known row.

    publication_at is the source publication time; observed_at is the earliest
    independently evidenced time our pipeline could have seen the exact payload.
    Both must be <= decision_at. No inference from event_at or archive capture.
    """
    decision = _utc(decision_at, "decision_at")
    seen = set()
    eligible = []
    for row in events:
        if not isinstance(row, Mapping):
            raise PITAvailabilityError("row: mapping required")
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise PITAvailabilityError("event_id: nonempty string required")
        if event_id in seen:
            raise PITAvailabilityError(f"duplicate event_id: {event_id}")
        seen.add(event_id)
        published = _utc(row.get("publication_at"), "publication_at")
        observed = _utc(row.get("observed_at"), "observed_at")
        if observed < published:
            raise PITAvailabilityError(f"{event_id}: observation precedes publication")
        if published > decision or observed > decision:
            raise PITAvailabilityError(f"{event_id}: not available at decision")
        eligible.append(event_id)
    return tuple(eligible)
