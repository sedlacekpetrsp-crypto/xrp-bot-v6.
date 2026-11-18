"""K10 offline attribution conflict gate; no network, trading, or performance logic.

Evidence records are immutable observations, not assertions of true exchange ownership.
A conflict or missing independent corroboration must fail closed.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class Evidence:
    address: str
    exchange: str
    source_id: str
    captured_at: datetime
    published_at: datetime


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("naive timestamp")
    return value.astimezone(timezone.utc)


def validate_attribution(
    records: Iterable[Evidence], decision_at: datetime, min_sources: int = 2
) -> dict[str, str]:
    """Return accepted address->exchange only for consistent independent PIT sources.

    All observations for an address must agree, including late observations: late
    evidence is rejected rather than silently excluded. Source IDs identify
    independent publishers; multiple snapshots of one publisher count once.
    """
    cutoff = _utc(decision_at)
    if min_sources < 2:
        raise ValueError("independent corroboration requires at least two sources")
    grouped: dict[str, dict[str, set[str]]] = {}
    seen: set[tuple[str, str, str, datetime, datetime]] = set()
    for item in records:
        address = item.address.strip()
        exchange = item.exchange.strip()
        source = item.source_id.strip()
        if not address or not exchange or not source:
            raise ValueError("blank attribution field")
        published, captured = _utc(item.published_at), _utc(item.captured_at)
        if published > captured or captured > cutoff:
            raise ValueError("unavailable evidence at decision time")
        key = (address, exchange, source, published, captured)
        if key in seen:
            raise ValueError("duplicate evidence")
        seen.add(key)
        grouped.setdefault(address, {}).setdefault(exchange, set()).add(source)
    accepted = {}
    for address, labels in grouped.items():
        if len(labels) != 1:
            raise ValueError(f"conflicting exchange attribution: {address}")
        exchange, sources = next(iter(labels.items()))
        if len(sources) >= min_sources:
            accepted[address] = exchange
    return accepted
