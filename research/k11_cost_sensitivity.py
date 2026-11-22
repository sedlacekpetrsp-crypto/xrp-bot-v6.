"""K11 ex-ante cost sensitivity diagnostics; no market returns or backtests.

The bound must be supplied from independent, documented economic evidence.
This module deliberately cannot convert a sensitivity pass into DATA GO.
"""
from dataclasses import dataclass
from math import isfinite
from research.k11_cost_floor import CostAssumptions, round_trip_cost


@dataclass(frozen=True)
class BoundEvidence:
    gross_upper_bound: float | None
    source_id: str | None
    available_at: str | None


def assess_sensitivity(evidence: BoundEvidence, assumptions: CostAssumptions) -> dict:
    """Fail closed on absent evidence; show cost viability at x1/x2/x3.

    Timestamp provenance must be reviewed externally; a string is not proof
    of point-in-time availability. This function never grants permission to
    run performance tests.
    """
    costs = {f"x{n}": round_trip_cost(assumptions, n) for n in (1, 2, 3)}
    bound = evidence.gross_upper_bound
    if bound is None or not evidence.source_id or not evidence.available_at:
        return {"verdict": "DATA_BLOCKED", "costs": costs, "margins": None,
                "passes": None, "pit_verified": False}
    if isinstance(bound, bool) or not isinstance(bound, (float, int)) or not isfinite(bound) or bound < 0:
        raise ValueError("upper bound must be finite and nonnegative")
    margins = {key: bound - cost for key, cost in costs.items()}
    passes = {key: margin > 0 for key, margin in margins.items()}
    verdict = "COST_NO_GO" if not passes["x1"] else "NOT_DISPROVEN"
    return {"verdict": verdict, "costs": costs, "margins": margins,
            "passes": passes, "pit_verified": False}
