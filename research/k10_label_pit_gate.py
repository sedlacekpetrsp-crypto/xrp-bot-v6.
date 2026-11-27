"""K10 data-only point-in-time exchange address label gate.

No network, trading, historical performance or price inputs. An archive snapshot
proves that a label was publicly visible by a given timestamp; it does not prove
that the attribution was correct. Caller must independently verify archive bytes
against sha256 and the exchange identity evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
import re

_ACCOUNT = re.compile(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ArchivedLabel:
    account: str
    exchange: str
    captured_at: datetime
    content_sha256: str
    source_url: str


def _utc(t: datetime) -> datetime:
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone-aware UTC datetime required")
    if t.utcoffset().total_seconds() != 0:
        raise ValueError("UTC offset must be zero")
    return t.astimezone(timezone.utc)


def validate_labels(labels: list[ArchivedLabel], sample_start: datetime) -> dict[str, ArchivedLabel]:
    """Fail closed on absent/late/ambiguous provenance, never silently re-label."""
    start = _utc(sample_start)
    if not labels:
        raise ValueError("no archived labels")
    by_account: dict[str, ArchivedLabel] = {}
    for label in labels:
        if not _ACCOUNT.fullmatch(label.account):
            raise ValueError("invalid XRPL classic address")
        if not label.exchange.strip() or not label.source_url.startswith("https://"):
            raise ValueError("missing exchange or HTTPS provenance")
        if not _SHA.fullmatch(label.content_sha256):
            raise ValueError("invalid lowercase SHA-256")
        if _utc(label.captured_at) >= start:
            raise ValueError("label snapshot not strictly prior to sample")
        prior = by_account.get(label.account)
        if prior is not None:
            raise ValueError("duplicate or conflicting account label")
        by_account[label.account] = label
    return by_account


def volume_coverage(
    payments: list[tuple[str, float]],
    labels: dict[str, ArchivedLabel],
    threshold: float = 0.80,
) -> tuple[float, bool]:
    """Data coverage only; amount is positive XRP, not a return or trade."""
    if isinstance(threshold, bool) or not isinstance(threshold, (float, int)) or not isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError("invalid threshold")
    total = covered = 0.0
    for destination, amount in payments:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount <= 0:
            raise ValueError("invalid XRP amount")
        total += amount
        if destination in labels:
            covered += amount
    if not payments or not isfinite(total) or total <= 0:
        raise ValueError("missing or overflowing payment volume")
    ratio = covered / total
    return ratio, ratio >= threshold
