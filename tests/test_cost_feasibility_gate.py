"""Synthetic-only diagnostic tests: no market data or performance evaluation."""
import pytest
from research.cost_feasibility_gate import assess_cost_feasibility


def gate(**kwargs):
    defaults = dict(fee_per_side="0.00095", slippage_per_side="0.0002",
                    adverse_funding_roundtrip="0", gross_upper_bound="0.003")
    defaults.update(kwargs)
    return assess_cost_feasibility(**defaults)


def test_baseline_and_sensitivity():
    result = gate()
    assert tuple(str(x) for x in result.roundtrip_costs) == (
        "0.00230", "0.00460", "0.00690")
    assert result.verdict == "NECESSARY_ONLY"


def test_break_even_fails_closed():
    assert gate(gross_upper_bound="0.00230").verdict == "NO_GO_COST_BOUND"


def test_funding_is_adverse_and_not_multiplied():
    result = gate(adverse_funding_roundtrip="0.0003")
    assert result.roundtrip_costs[0] == result.fee_per_side * 2 + result.slippage_per_side * 2 + result.adverse_funding_roundtrip


def test_below_cost_is_rejected():
    assert gate(gross_upper_bound="0.001").verdict == "NO_GO_COST_BOUND"


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-0.1", "1", True, None, "abc"])
def test_invalid_cost_inputs_fail_closed(bad):
    with pytest.raises(ValueError):
        gate(fee_per_side=bad)


@pytest.mark.parametrize("factors", [(), (0, 1), (1, 1), (3, 2), ("NaN",)])
def test_invalid_sensitivity_fails_closed(factors):
    with pytest.raises(ValueError):
        gate(sensitivity=factors)


def test_cost_bound_not_a_go_signal():
    assert gate(gross_upper_bound="0.1").verdict != "GO"
