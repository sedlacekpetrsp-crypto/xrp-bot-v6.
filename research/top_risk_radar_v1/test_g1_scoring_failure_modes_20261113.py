"""Synthetic-only G1 scoring failure-mode regressions (no OOS fit or performance run).

Protects fail-closed scoring for Top Risk and Early Growth on identical rows.
"""
import math

import pytest

from research.top_risk_radar_v1.calibration_metrics import (
    SCORING_VERSION, brier_score, brier_skill_score, calibration_bins,
    log_loss, score,
)


@pytest.mark.parametrize("bad_label", [True, False, None, 0.0, 1.0, "0", "1", -1, 2])
def test_immature_or_nonbinary_labels_fail_closed(bad_label):
    with pytest.raises((TypeError, ValueError)):
        score([0.2], [bad_label])


@pytest.mark.parametrize("bad_probability", [True, False, -0.01, 1.01, math.nan, math.inf, -math.inf, None, "0.5"])
def test_invalid_probability_is_not_silently_clipped(bad_probability):
    with pytest.raises((TypeError, ValueError)):
        score([bad_probability], [0])


def test_zero_reference_brier_is_undefined_not_false_success():
    assert brier_skill_score([0.1, 0.9], [0.0, 1.0], [0, 1]) is None


def test_identical_predictions_have_zero_skill_even_with_imbalanced_events():
    y = [0] * 19 + [1]
    p = [0.05] * len(y)
    assert brier_skill_score(p, p, y) == pytest.approx(0.0)


def test_mismatched_model_reference_rows_rejected():
    with pytest.raises(ValueError, match="identical rows"):
        brier_skill_score([0.2], [0.2, 0.4], [0])


def test_false_certainty_in_log_loss_is_infinite_unless_predeclared_clip():
    assert math.isinf(log_loss([0.0, 1.0], [1, 0]))
    assert math.isfinite(log_loss([0.0, 1.0], [1, 0], eps=1e-6))


def test_clipping_parameter_is_visible_in_scoring_record():
    record = score([0.0, 1.0], [1, 0], eps=1e-6)
    assert record["scoring_version"] == SCORING_VERSION
    assert record["log_loss_eps"] == 1e-6
    assert record["status"] == "diagnostic_only"


@pytest.mark.parametrize("eps", [0.0, 0.5, 1.0, -0.1, True, math.nan, None])
def test_invalid_or_unclipped_epsilon_never_masquerades_as_clipped(eps):
    if eps is None:
        assert math.isinf(log_loss([0.0], [1], eps=eps))
    else:
        with pytest.raises(ValueError):
            log_loss([0.0], [1], eps=eps)


def test_calibration_bin_right_edge_and_empty_bins():
    bins = calibration_bins([0.0, 1.0], [0, 1], bins=10)
    assert len(bins) == 10
    assert bins[0]["count"] == bins[9]["count"] == 1
    assert bins[0]["event_rate"] == 0.0
    assert bins[9]["event_rate"] == 1.0
    assert all(b["count"] == 0 and b["mean_prediction"] is None
               and b["event_rate"] is None for b in bins[1:9])


def test_brier_score_does_not_confuse_class_prevalence_with_skill():
    y = [0, 0, 0, 1]
    assert brier_score([0.25] * 4, y) == pytest.approx(0.1875)
    assert brier_skill_score([0.25] * 4, [0.25] * 4, y) == pytest.approx(0.0)
