"""Pre-performance cost feasibility gate. No market data or backtest.

All rates are fractions of notional, per side. This intentionally does not
model fills, leverage, funding, spread changes or market impact.
"""
from decimal import Decimal, InvalidOperation

def _rate(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid cost rate") from exc
    if not result.is_finite() or result < 0 or result >= 1:
        raise ValueError("rate must be finite and in [0, 1)")
    return result

def minimum_gross_move(fee_per_side="0.00095", slippage_per_side="0.0002",
                       extra_buffer="0"):
    """Minimum favorable price move as fraction of entry price, for long roundtrip.

    Assumes entry cash paid = P*(1+fee+slippage), and exit cash received =
    P*(1+move)*(1-fee-slippage). Equal entry/exit notional units.
    This is an algebraic break-even hurdle, NOT expected profitability.
    """
    fee, slip, buffer = map(_rate, (fee_per_side, slippage_per_side, extra_buffer))
    side = fee + slip
    if side >= 1:
        raise ValueError("combined per-side costs >= 100%")
    return (Decimal(1) + side + buffer) / (Decimal(1) - side) - Decimal(1)

def classify_gross_target(target, **kwargs):
    """Only a necessary cost hurdle; PASS does not imply profitable strategy."""
    t = _rate(target)
    hurdle = minimum_gross_move(**kwargs)
    return "BELOW_COST_FLOOR" if t <= hurdle else "ABOVE_COST_FLOOR_UNVALIDATED"
