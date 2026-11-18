"""K10 data-only audit: distinguish RPC feasibility samples from cohort evidence.

No market prices, trades, signals, or performance calculations.
"""
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SampleAudit:
    requested: tuple[int, ...]
    observed: tuple[int, ...]
    full_census: bool
    coverage_claim_allowed: bool
    reason: str


def audit_ledger_sample(start: int, end: int, requested: Sequence[int],
                        observed: Sequence[int]) -> SampleAudit:
    """Inclusive window. Fail closed on missing, duplicated or off-window IDs."""
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise ValueError("invalid inclusive ledger window")
    for values in (requested, observed):
        if any(type(i) is not int or i < start or i > end for i in values):
            raise ValueError("ledger index outside pre-registered window")
        if len(values) != len(set(values)):
            raise ValueError("duplicate ledger index")
    req = tuple(requested)
    obs = tuple(observed)
    if not req:
        raise ValueError("empty feasibility sample")
    if set(obs) != set(req):
        raise ValueError("missing or unsolicited ledger responses")
    census = len(req) == end - start + 1
    return SampleAudit(req, obs, census, census,
                       "full census" if census else
                       "sparse feasibility probe: cannot establish top-N cohort, "
                       "historical label coverage, or recipient ranking")


def assert_cohort_evidence(audit: SampleAudit) -> None:
    """Never silently promote a sparse RPC probe into a cohort DATA GO."""
    if not audit.coverage_claim_allowed:
        raise ValueError(audit.reason)
