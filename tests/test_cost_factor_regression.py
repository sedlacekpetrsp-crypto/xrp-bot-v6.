"""Offline regression tests: cost multipliers are not fractional rates."""
from decimal import Decimal
import pytest
from research.cost_feasibility_gate import assess_cost_feasibility


def gate(**overrides):
    args = dict(fee_per_side="0.00095", slippage_per_side="0.0002",
                adverse_funding_roundtrip="0.0003",
                gross_upper_bound="0.01")
    args.update(overrides)
    return assess_cost_feasibility(**args)


def test_standard_three_sensitivities_are_accepted():
    result = gate()
    assert result.sensitivity == (Decimal("1"), Decimal("2"), Decimal("3"))
    assert result.roundtrip_costs == (Decimal("0.00260"),
                                      Decimal("0.00490"), Decimal("0.00720"))
    assert result.verdict == "NECESSARY_ONLY"


def test_exact_break_even_is_not_positive_edge():
    assert gate(gross_upper_bound="0.00260").verdict == "NO_GO_COST_BOUND"


@pytest.mark.parametrize("factors", [(1, 1), (2, 1), (0, 1), (1, float("nan")),
                                      (1, float("inf")), (True, 2), ("bad", 2)])
def test_invalid_multipliers_fail_closed(factors):
    with pytest.raises(ValueError):
        gate(sensitivity=factors)


def test_larger_multipliers_are_valid_and_ordered():
    assert gate(sensitivity=(1, 3, 10)).roundtrip_costs[-1] == Decimal("0.02330")
