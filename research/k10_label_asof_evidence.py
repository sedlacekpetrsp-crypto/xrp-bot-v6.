"""Fail-closed K10 label availability gate; diagnostic only, no trading/performance."""
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

@dataclass(frozen=True)
class LabelEvidence:
    address: str
    label: str
    first_public_at: datetime
    captured_at: datetime
    source_id: str

def _utc(t: datetime) -> bool:
    return (isinstance(t, datetime) and t.tzinfo is not None
            and t.utcoffset() is not None and t.utcoffset().total_seconds() == 0)

def asof_labels(
    addresses: Sequence[str], evidence: Sequence[LabelEvidence], decision_at: datetime
) -> Mapping[str, str]:
    """Return only independently evidenced labels available by decision time.

    Missing evidence remains UNKNOWN, never inferred from present-day address lists.
    Duplicated/conflicting records fail closed rather than selecting favorable labels.
    This gate does not prove that a claimed publication timestamp is authentic.
    """
    if not _utc(decision_at):
        raise ValueError("decision_at must be timezone-aware UTC")
    if not addresses or any(not isinstance(a, str) or not a.strip() for a in addresses):
        raise ValueError("invalid addresses")
    if len(set(addresses)) != len(addresses):
        raise ValueError("duplicate addresses")
    allowed = set(addresses)
    result = {}
    seen = set()
    for item in evidence:
        if not isinstance(item, LabelEvidence):
            raise ValueError("invalid evidence")
        if (item.address not in allowed or item.address in seen
                or not item.label.strip() or not item.source_id.strip()
                or not _utc(item.first_public_at) or not _utc(item.captured_at)
                or item.first_public_at > item.captured_at):
            raise ValueError("invalid, conflicting, or non-PIT label evidence")
        seen.add(item.address)
        if item.first_public_at <= decision_at and item.captured_at <= decision_at:
            result[item.address] = item.label
    return result
