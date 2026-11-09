"""Synthetic contract checks for descriptive prevalence priors (PAPER only).

These tests use no market data, do not fit a model and do not evaluate OOS
predictive performance. They guard label maturity and fail-closed inputs.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.prevalence_baseline import (
    Observation,
    historical_prevalence,
)

CUT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def obs(days_before, growth=None, downside=None):
    return Observation(CUT - timedelta(days=days_before), growth, downside)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_exact_maturity_boundary_is_inclusive(target, horizon):
    rows = [obs(horizon, True, True), obs(horizon - 1, False, False)]
    result = historical_prevalence(rows, CUT, horizon_days=horizon, target=target)
    assert result == {"status": "descriptive_baseline", "n": 1, "rate": 1.0}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_unknown_mature_labels_do_not_count_as_negative(target, horizon):
    rows = [obs(horizon + 1, None, None), obs(horizon + 2, True, True)]
    result = historical_prevalence(rows, CUT, horizon_days=horizon, target=target)
    assert (result["n"], result["rate"]) == (1, 1.0)


def test_other_target_label_does_not_contaminate_growth_prevalence():
    rows = [obs(40, True, False), obs(41, False, True)]
    result = historical_prevalence(rows, CUT, horizon_days=30, target="growth")
    assert (result["n"], result["rate"]) == (2, 0.5)


def test_train_timestamp_validation_applies_even_to_future_rows():
    rows = [Observation(CUT.replace(tzinfo=None) + timedelta(days=1), None, None)]
    with pytest.raises(ValueError, match="timezone-aware"):
        historical_prevalence(rows, CUT, horizon_days=14, target="downside")


@pytest.mark.parametrize("bad", [float("nan"), 0.0, "true", 2])
def test_selected_target_rejects_non_boolean_mature_labels(bad):
    with pytest.raises(TypeError, match="bool or None"):
        historical_prevalence([obs(40, bad, False)], CUT, horizon_days=30, target="growth")


def test_aware_offset_test_cutoff_is_same_instant():
    local = CUT.astimezone(timezone(timedelta(hours=5, minutes=30)))
    rows = [obs(30, True, None)]
    assert historical_prevalence(rows, local, horizon_days=30, target="growth")["rate"] == 1.0
