"""Conformance tests for the canonical radar scoring contract (radar-scoring-v1).

Replaces 10 earlier calibration test files written against three divergent APIs.
Synthetic inputs only: no historical observations, predictions, fitting or performance runs.
"""
import math
import random

import pytest

from research.top_risk_radar_v1 import calibration_metrics as cm
from research.top_risk_radar_v1.calibration_metrics import (
    SCORING_VERSION, brier_score, brier_skill_score, calibration_bins, log_loss, score,
)


# --- known values -----------------------------------------------------------
def test_perfect_probabilities_have_zero_error():
    assert brier_score([0.0, 1.0], [0, 1]) == 0.0
    assert log_loss([0.0, 1.0], [0, 1]) == 0.0


def test_half_probability_has_known_scores():
    assert brier_score([0.5, 0.5], [0, 1]) == pytest.approx(0.25)
    assert log_loss([0.5, 0.5], [0, 1]) == pytest.approx(math.log(2))


def test_climatology_brier_equals_event_variance():
    y = [1, 0, 0, 0]
    assert brier_score([0.25] * 4, y) == pytest.approx(0.25 * 0.75)


# --- log-loss policy (divergence item 1) ------------------------------------
def test_false_certainty_is_infinite_by_default():
    assert math.isinf(log_loss([0.0, 1.0], [1, 0]))
    assert math.isinf(log_loss([1.0], [0]))


def test_explicit_eps_clips_and_is_reported():
    eps = 1e-15
    value = log_loss([0.0, 1.0], [1, 0], eps=eps)
    assert value == pytest.approx(-math.log(eps), rel=1e-3)
    record = score([0.0, 1.0], [1, 0], eps=eps)
    assert record["log_loss_eps"] == eps and math.isfinite(record["log_loss"])
    assert score([0.5], [1])["log_loss_eps"] is None


def test_eps_does_not_change_interior_probabilities():
    p, y = [0.2, 0.7, 0.9], [0, 1, 1]
    assert log_loss(p, y, eps=1e-6) == log_loss(p, y)


@pytest.mark.parametrize("bad", [0, 0.5, -1e-9, 1.0, True, "1e-15", float("nan")])
def test_invalid_eps_rejected(bad):
    with pytest.raises(ValueError):
        log_loss([0.5], [1], eps=bad)


# --- label / probability types (divergence item 2) ---------------------------
@pytest.mark.parametrize("invalid", [None, True, False, 2, -1, 0.5, 1.0, "1"])
def test_only_int_binary_outcomes_accepted(invalid):
    for fn in (brier_score, log_loss, calibration_bins, score):
        with pytest.raises(ValueError):
            fn([0.5], [invalid])


@pytest.mark.parametrize("invalid", [-0.1, 1.1, float("nan"), float("inf")])
def test_out_of_range_probabilities_rejected(invalid):
    with pytest.raises(ValueError):
        brier_score([invalid], [1])


@pytest.mark.parametrize("invalid", [None, "0.5", True])
def test_non_numeric_probabilities_rejected(invalid):
    with pytest.raises(TypeError):
        score([invalid], [0])


def test_length_mismatch_and_empty_rejected():
    for args in (([], []), ([0.5], []), ([0.5, 0.6], [1])):
        with pytest.raises(ValueError):
            score(*args)


# --- bins (divergence item 3) ------------------------------------------------
def test_all_bins_returned_including_empty():
    rows = calibration_bins([0.05, 0.95], [0, 1], bins=4)
    assert [r["count"] for r in rows] == [1, 0, 0, 1]
    assert rows[1]["mean_prediction"] is None and rows[1]["event_rate"] is None
    assert rows[0]["lower"] == 0.0 and rows[-1]["upper"] == 1.0


def test_boundary_one_belongs_to_last_bin():
    rows = calibration_bins([0.0, 0.5, 1.0], [0, 1, 1], bins=2)
    assert rows[0]["count"] == 1 and rows[1]["count"] == 2
    assert rows[1]["mean_prediction"] == pytest.approx(0.75)


@pytest.mark.parametrize("invalid", [0, 1, 101, True, 2.0, -1])
def test_bin_count_bounds(invalid):
    with pytest.raises(ValueError):
        calibration_bins([0.5], [1], bins=invalid)
    assert len(calibration_bins([0.5], [1], bins=cm.MAX_BINS)) == 100


# --- proper-scoring / metamorphic properties ----------------------------------
def test_sharper_correct_forecast_scores_better():
    y = [1, 0, 1, 0]
    sharp = [0.9 if v else 0.1 for v in y]
    weak = [0.6 if v else 0.4 for v in y]
    assert brier_score(sharp, y) < brier_score(weak, y)
    assert log_loss(sharp, y) < log_loss(weak, y)


def test_expected_brier_minimised_at_true_probability():
    q = 0.3
    expected = lambda p: q * (p - 1) ** 2 + (1 - q) * p ** 2
    assert all(expected(q) <= expected(p) for p in [i / 100 for i in range(101)])


def test_permutation_invariance_and_determinism():
    rng = random.Random(7)
    p = [rng.random() for _ in range(50)]
    y = [int(rng.random() < v) for v in p]
    order = list(range(50))
    rng.shuffle(order)
    a = score(p, y, bins=5)
    b = score([p[i] for i in order], [y[i] for i in order], bins=5)
    assert a["brier"] == pytest.approx(b["brier"]) and a["log_loss"] == pytest.approx(b["log_loss"])
    assert [r["count"] for r in a["bins"]] == [r["count"] for r in b["bins"]]
    assert score(p, y, bins=5) == a


# --- skill vs reference (P0-1 primary diagnostic) ----------------------------
def test_brier_skill_vs_climatology():
    y = [1, 0, 0, 0]
    ref = [0.25] * 4
    assert brier_skill_score(ref, ref, y) == pytest.approx(0.0)
    assert brier_skill_score([0.9, 0.1, 0.1, 0.1], ref, y) > 0
    assert brier_skill_score([0.1, 0.9, 0.9, 0.9], ref, y) < 0


def test_brier_skill_undefined_for_perfect_reference_and_mismatch():
    assert brier_skill_score([0.5, 0.5], [0.0, 1.0], [0, 1]) is None
    with pytest.raises(ValueError):
        brier_skill_score([0.5], [0.5, 0.5], [1])


def test_score_record_schema_is_versioned():
    record = score([0.2, 0.8], [0, 1], bins=2)
    assert record["scoring_version"] == SCORING_VERSION == "radar-scoring-v1"
    assert set(record) == {"scoring_version", "status", "n", "event_rate", "brier",
                           "log_loss", "log_loss_eps", "bins"}
    assert record["status"] == "diagnostic_only" and record["n"] == 2


def test_single_canonical_module():
    import importlib.util
    for legacy in ("calibration", "calibration_diagnostics"):
        assert importlib.util.find_spec(f"research.top_risk_radar_v1.{legacy}") is None
