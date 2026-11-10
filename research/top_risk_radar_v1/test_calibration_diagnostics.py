"""Synthetic unit tests only: no predictive OOS validation or backtest."""
import pytest

from research.top_risk_radar_v1.calibration_diagnostics import binary_calibration_diagnostics as diagnostics


def test_empty_is_explicitly_insufficient():
    assert diagnostics([], []) == {"status": "insufficient_oos", "n": 0, "brier": None, "bins": []}


def test_perfect_predictions_and_upper_bin_boundary():
    result = diagnostics([0.0, 1.0], [False, True], bins=2)
    assert result["status"] == "diagnostics_only_not_validated"
    assert result["n"] == 2
    assert result["brier"] == 0
    assert [row["n"] for row in result["bins"]] == [1, 1]
    assert [row["observed_rate"] for row in result["bins"]] == [0.0, 1.0]


def test_brier_and_empty_bin_are_unambiguous():
    result = diagnostics([0.25, 0.75], [True, False], bins=4)
    assert result["brier"] == pytest.approx(0.5625)
    assert result["bins"][0]["n"] == 0
    assert result["bins"][0]["observed_rate"] is None
    assert result["bins"][1]["mean_predicted"] == 0.25
    assert result["bins"][3]["observed_rate"] == 0.0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.01, 1.01, True, "0.5", None])
def test_invalid_probability_fails_closed(bad):
    with pytest.raises(ValueError, match="probabilities"):
        diagnostics([bad], [False])


@pytest.mark.parametrize("bad", [1, 0, "True", None])
def test_nonboolean_outcome_fails_closed(bad):
    with pytest.raises(TypeError, match="outcomes"):
        diagnostics([0.5], [bad])


@pytest.mark.parametrize("bad", [True, 1, 101, 2.5, "10"])
def test_invalid_bin_count_fails_closed(bad):
    with pytest.raises(ValueError, match="bins"):
        diagnostics([0.5], [True], bins=bad)


def test_mismatched_lengths_fail_closed():
    with pytest.raises(ValueError, match="equal length"):
        diagnostics([0.1, 0.2], [True])


@pytest.mark.parametrize("probability,expected_bin", [
    (0.0, 0), (0.249999999, 0), (0.25, 1),
    (0.499999999, 1), (0.5, 2), (0.75, 3), (1.0, 3),
])
def test_reliability_bins_are_left_closed_right_open_except_final(probability, expected_bin):
    result = diagnostics([probability], [False], bins=4)
    assert [row["n"] for row in result["bins"]] == [int(i == expected_bin) for i in range(4)]
    assert result["bins"][expected_bin]["mean_predicted"] == probability


def test_calibration_is_invariant_to_order_of_pairs():
    probabilities = [0.1, 0.9, 0.3, 0.7]
    outcomes = [False, True, True, False]
    original = diagnostics(probabilities, outcomes, bins=2)
    reordered = diagnostics(list(reversed(probabilities)), list(reversed(outcomes)), bins=2)
    assert reordered["n"] == original["n"]
    assert reordered["brier"] == pytest.approx(original["brier"])
    for left, right in zip(original["bins"], reordered["bins"]):
        assert left["n"] == right["n"]
        assert left["observed_rate"] == right["observed_rate"]
        assert left["mean_predicted"] == pytest.approx(right["mean_predicted"])


def test_diagnostics_do_not_mutate_caller_inputs():
    probabilities = [0.2, 0.8]
    outcomes = [False, True]
    before_probabilities = probabilities.copy()
    before_outcomes = outcomes.copy()
    diagnostics(probabilities, outcomes, bins=2)
    assert probabilities == before_probabilities
    assert outcomes == before_outcomes
