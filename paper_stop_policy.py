"""PAPER initial-stop overlay applied AFTER original quantity/target sizing.

Baseline risk fields remain the sizing/R-multiple reference so quantity, TP,
break-even and profit-lock rules do not change. stop_loss_risk_net reports the
actual estimated loss at the widened initial stop, including fees/slippage.
No restored or trailing stop is multiplied again.
"""
import math
import os

MULTIPLIER = float(os.getenv("PAPER_STOP_DISTANCE_MULTIPLIER", "1.0"))
if not math.isfinite(MULTIPLIER) or not 1.0 <= MULTIPLIER <= 1.15:
    raise ValueError("PAPER stop multiplier must be between 1.0 and 1.15")
POLICY = "PAPER-SL-20261013-KEEP-QTY"


def apply(position, fee=0.0, slip=0.0):
    """Widen a newly created loss-side stop once; never change quantity or TP."""
    if MULTIPLIER == 1.0 or position.get("stop_loss_policy") == POLICY:
        return position
    entry = float(position.get("entry_price", position.get("entry")))
    key = "stop_loss" if "stop_loss" in position else "stop"
    stop = float(position[key])
    qty = float(position["qty"])
    side = 1 if position["side"] == "LONG" else -1 if position["side"] == "SHORT" else 0
    values = (entry, stop, qty, fee, slip)
    if not all(math.isfinite(x) for x in values) or min(entry, stop, qty) <= 0 or not side:
        raise ValueError("Invalid PAPER stop inputs")
    distance = side * (entry - stop)
    if distance <= 0:
        return position  # never loosen a break-even/profit-protecting stop
    widened = entry - side * distance * MULTIPLIER
    if widened <= 0:
        raise ValueError("Invalid widened PAPER stop")
    fill = widened * (1 - side * slip)
    loss = qty * (side * (entry - fill) + fee * (entry + fill))
    position.update(stop_loss_policy=POLICY, stop_loss_multiplier=MULTIPLIER,
                    stop_loss_original=stop, stop_loss_risk_net=loss,
                    risk_reference="original sizing and exit thresholds; actual initial SL risk is stop_loss_risk_net")
    position[key] = widened
    if "initial_stop" in position:
        position["initial_stop"] = widened
    return position


def status():
    return dict(policy=POLICY, initial_stop_distance_multiplier=MULTIPLIER,
                position_sizing="unchanged", take_profit="unchanged",
                trailing_and_breakeven="unchanged", applies_to="new PAPER positions")
