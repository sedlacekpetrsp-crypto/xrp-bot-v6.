"""Pre-performance, synthetic-only cost feasibility gate for PAPER research.

This gate is not a backtest or evidence of alpha. Inputs must be declared ex ante.
All rates are fractions of notional (0.00095 = 0.095%).
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


def _rate(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a rate")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name}: invalid rate") from None
    if not result.is_finite() or result < 0 or result >= 1:
        raise ValueError(f"{name}: must be finite and in [0,1)")
    return result


def _factor(value):
    """Finite positive multiplier; unlike a rate, may exceed 100%."""
    if isinstance(value, bool):
        raise ValueError("sensitivity factor: boolean is invalid")
    try:
        factor = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("sensitivity factor: invalid number") from None
    if not factor.is_finite() or factor < 1:
        raise ValueError("sensitivity factor: must be finite and >= 1")
    return factor


@dataclass(frozen=True)
class CostGate:
    fee_per_side: Decimal
    slippage_per_side: Decimal
    adverse_funding_roundtrip: Decimal
    sensitivity: tuple
    roundtrip_costs: tuple
    gross_upper_bound: Decimal
    verdict: str


def assess_cost_feasibility(*, fee_per_side, slippage_per_side,
                            adverse_funding_roundtrip, gross_upper_bound,
                            sensitivity=(1, 2, 3)):
    """Reject only when an ex-ante defensible gross upper bound cannot cover costs.

    If upper bound equals a cost, break-even is not positive: reject.
    A passing bound is NOT a profitable strategy, only a necessary-condition check.
    """
    fee = _rate(fee_per_side, "fee_per_side")
    slip = _rate(slippage_per_side, "slippage_per_side")
    funding = _rate(adverse_funding_roundtrip, "adverse_funding_roundtrip")
    bound = _rate(gross_upper_bound, "gross_upper_bound")
    factors = tuple(_factor(x) for x in sensitivity)
    if not factors or any(x < 1 for x in factors) or len(set(factors)) != len(factors):
        raise ValueError("sensitivity must be unique factors >= 1")
    if tuple(sorted(factors)) != factors:
        raise ValueError("sensitivity factors must be increasing")
    costs = tuple((fee + slip) * 2 * factor + funding for factor in factors)
    verdict = "NO_GO_COST_BOUND" if bound <= costs[0] else "NECESSARY_ONLY"
    return CostGate(fee, slip, funding, factors, costs, bound, verdict)
