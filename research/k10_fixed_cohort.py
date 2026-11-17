"""K10 data-only fixed-cohort coverage audit; never selects cohort by label status.

The cohort must be frozen from an independently timestamped pre-sample ranking.
No historical trading performance, network requests, or order execution.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import fsum, isfinite
from typing import Mapping, Sequence

@dataclass(frozen=True)
class CohortMember:
    address: str
    ranked_at: datetime
    rank: int

def fixed_cohort_coverage(
    cohort: Sequence[CohortMember],
    destination_xrp: Mapping[str, float],
    pit_labels: Mapping[str, object],
    sample_start: datetime,
    threshold: float = 0.80,
) -> tuple[float, bool]:
    """Return labeled share of ALL frozen-cohort destination volume.

    Unknown accounts stay in denominator. Non-cohort transfers are not counted.
    Ranking must be frozen strictly before sample_start. No top-N selection here.
    """
    if not isinstance(sample_start, datetime) or sample_start.tzinfo is None or sample_start.utcoffset() is None or sample_start.utcoffset().total_seconds() != 0:
        raise ValueError("sample_start must be UTC")
    if not isinstance(threshold, (float, int)) or isinstance(threshold, bool) or not isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError("invalid threshold")
    if not cohort:
        raise ValueError("empty preselected cohort")
    addresses = set()
    ranks = set()
    for member in cohort:
        if not isinstance(member, CohortMember) or not member.address or member.address in addresses or isinstance(member.rank, bool) or not isinstance(member.rank, int) or member.rank < 1 or member.rank in ranks:
            raise ValueError("invalid or duplicate frozen cohort")
        t = member.ranked_at
        if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None or t.utcoffset().total_seconds() != 0 or t >= sample_start:
            raise ValueError("cohort ranking not PIT")
        addresses.add(member.address)
        ranks.add(member.rank)
    if ranks != set(range(1, len(cohort) + 1)):
        raise ValueError("cohort rank gaps")
    if set(destination_xrp) != addresses:
        raise ValueError("all and only cohort destinations required, including unknowns")
    amounts = []
    labeled = []
    for member in cohort:
        amount = destination_xrp[member.address]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount < 0:
            raise ValueError("invalid volume")
        amounts.append(float(amount))
        if member.address in pit_labels:
            labeled.append(float(amount))
    total = fsum(amounts)
    if not isfinite(total) or total <= 0:
        raise ValueError("zero or nonfinite denominator")
    ratio = fsum(labeled) / total
    return ratio, ratio >= threshold
