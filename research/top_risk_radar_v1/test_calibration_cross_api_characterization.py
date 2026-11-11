"""Synthetic cross-API characterization tests; no market data or performance runs.

These tests deliberately freeze *current* differences, not endorse either API
as canonical. Do not interchange the outputs in an OOS report.
"""
import math

import pytest

from research.top_risk_radar_v1.calibration import calibration_metrics as row_metrics
from research.top_risk_radar_v1.calibration_metrics import (
    brier_score, log_loss, calibration_bins,
)


def test_interior_probabilities_have_matching_proper_scores():
    probabilities = [0.1, 0.25, 0.5, 0.8, 0.9]
    outcomes = [0, 1, 0, 1, 1]
    result = row_metrics(list(zip(probabilities, map(bool, outcomes))), bins=5)
    assert result["brier"] == pytest.approx(brier_score(probabilities, outcomes))
    assert result["log_loss"] == pytest.approx(log_loss(probabilities, outcomes))


@pytest.mark.parametrize("probability,outcome", [(0.0, 1), (1.0, 0)])
def test_opposite_extreme_is_clipped_in_row_api_but_infinite_in_vector_api(probability, outcome):
    result = row_metrics([(probability, bool(outcome))])
    assert math.isfinite(result["log_loss"])
    assert math.isinf(log_loss([probability], [outcome]))
    assert result["brier"] == brier_score([probability], [outcome]) == 1.0


def test_label_type_contracts_are_intentionally_incompatible():
    with pytest.raises(TypeError):
        row_metrics([(0.5, 1)])
    with pytest.raises(ValueError):
        brier_score([0.5], [True])


def test_empty_bins_are_retained_only_by_row_api():
    row = row_metrics([(0.1, False)], bins=5)["bins"]
    vector = calibration_bins([0.1], [0], bins=5)
    assert len(row) == 5
    assert len(vector) == 1
    assert sum(item["n"] for item in row) == vector[0]["count"] == 1
    assert all(item["observed_rate"] is None for item in row if item["n"] == 0)


def test_more_than_one_hundred_bins_is_only_supported_by_vector_api():
    with pytest.raises(ValueError):
        row_metrics([(0.5, True)], bins=101)
    assert len(calibration_bins([0.5], [1], bins=101)) == 1


def test_unknown_labels_never_become_negative_in_either_api():
    with pytest.raises(TypeError):
        row_metrics([(0.5, None)])
    with pytest.raises(ValueError):
        log_loss([0.5], [None])
