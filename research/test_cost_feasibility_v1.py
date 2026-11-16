"""Synthetic unit tests; no historical performance evaluation."""
from decimal import Decimal
import pytest
from research.cost_feasibility_v1 import CostGate


def test_fee_slippage_break_even():
    gate = CostGate.from_rates("0.00095", "0.00095", "0.0002", "0.0002")
    threshold = gate.minimum_gross_return()
    assert threshold > Decimal("0.0023")
    assert threshold < Decimal("0.00231")
    assert abs(gate.net_return(threshold)) < Decimal("0.000000000000000000000001")


def test_zero_cost_identity_and_losses():
    gate = CostGate.from_rates(0, 0, 0, 0)
    assert gate.minimum_gross_return() == 0
    assert gate.net_return("-0.2") == Decimal("-0.2")


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-0.01", "1", True, 0.1])
def test_bad_cost_rates_fail_closed(bad):
    with pytest.raises(ValueError):
        CostGate.from_rates(bad, 0, 0, 0)


@pytest.mark.parametrize("bad", ["NaN", "-1", "-1.1", True, 0.1])
def test_bad_gross_return_fails_closed(bad):
    with pytest.raises(ValueError):
        CostGate.from_rates(0, 0, 0, 0).net_return(bad)


@pytest.mark.parametrize("bad", [Decimal("-0.1"), Decimal("1"), Decimal("NaN"), Decimal("Infinity"), True, 0.1])
def test_direct_constructor_rejects_invalid_rates(bad):
    with pytest.raises(ValueError):
        CostGate(bad, Decimal("0"), Decimal("0"), Decimal("0"))


def test_direct_constructor_normalizes_exact_values():
    gate = CostGate("0.00095", 0, Decimal("0.0002"), "0")
    assert all(isinstance(v, Decimal) for v in (
        gate.entry_fee, gate.exit_fee, gate.entry_slippage, gate.exit_slippage
    ))
    assert gate.minimum_gross_return() > 0
