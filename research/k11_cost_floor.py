"""Pre-performance cost feasibility gate for K11 delisting-event research.

Pure diagnostic. Does not fetch market data, estimate alpha, or place trades.
All rates are fractions of notional per side.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class CostAssumptions:
    fee_per_side: float = 0.00095
    slippage_per_side: float = 0.0002
    funding_round_trip: float = 0.0
    adverse_selection_round_trip: float = 0.0

    def __post_init__(self):
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")


def round_trip_cost(assumptions: CostAssumptions, multiplier: float = 1.0) -> float:
    """Conservative full round-trip cost; multiplier scales ALL cost components."""
    if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)) or not isfinite(multiplier) or multiplier < 1:
        raise ValueError("multiplier must be finite and >= 1")
    return multiplier * (2 * (assumptions.fee_per_side + assumptions.slippage_per_side)
                         + assumptions.funding_round_trip + assumptions.adverse_selection_round_trip)


def feasibility_gate(gross_edge_bound: float | None, assumptions: CostAssumptions) -> dict:
    """Only upper-bound logic: missing gross-edge evidence is DATA_BLOCKED.

    Gross edge must be an independently justified, nonnegative *upper bound*
    in fraction-of-notional units; it must not be fitted to final returns.
    """
    costs = {f"x{m}": round_trip_cost(assumptions, m) for m in (1, 2, 3)}
    if gross_edge_bound is None:
        return {"verdict": "DATA_BLOCKED", "costs": costs, "margin": None}
    if isinstance(gross_edge_bound, bool) or not isinstance(gross_edge_bound, (int, float)) or not isfinite(gross_edge_bound) or gross_edge_bound < 0:
        raise ValueError("gross_edge_bound must be finite and nonnegative")
    margin = gross_edge_bound - costs["x1"]
    return {"verdict": "COST_NO_GO" if margin <= 0 else "NOT_DISPROVEN",
            "costs": costs, "margin": margin}
