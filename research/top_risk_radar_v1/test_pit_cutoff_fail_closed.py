"""Additional synthetic fail-closed PIT boundary checks for descriptive XRP baselines.

No historical price data, predictive OOS scores, or performance backtest.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pit_prevalence import (
    PITObservation,
    pit_historical_prevalence,
)

CUTOFF = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_decision_at_cutoff_is_not_training_data(target, horizon):
    """Even a fabricated available label must not enter at the decision instant."""
    row = PITObservation(CUTOFF, CUTOFF, True, True)
    result = pit_historical_prevalence([row], CUTOFF, horizon_days=horizon, target=target)
    assert result == {"status": "insufficient_train", "n": 0, "rate": None}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_label_available_one_microsecond_after_cutoff_is_excluded(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 1)
    row = PITObservation(decision, CUTOFF + timedelta(microseconds=1), True, True)
    result = pit_historical_prevalence([row], CUTOFF, horizon_days=horizon, target=target)
    assert result == {"status": "insufficient_train", "n": 0, "rate": None}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_negative_one_microsecond_before_horizon_is_rejected(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 2)
    early = decision + timedelta(days=horizon) - timedelta(microseconds=1)
    row = PITObservation(
        decision, early,
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    with pytest.raises(ValueError, match="negative label available before horizon"):
        pit_historical_prevalence([row], CUTOFF, horizon_days=horizon, target=target)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_negative_exactly_at_horizon_is_allowed(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 1)
    row = PITObservation(
        decision, decision + timedelta(days=horizon),
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    assert pit_historical_prevalence(
        [row], CUTOFF, horizon_days=horizon, target=target
    ) == {"status": "descriptive_pit_baseline", "n": 1, "rate": 0.0}


@pytest.mark.parametrize("bad_label", [0, 1, "True", 0.0, [], {}])
def test_non_boolean_labels_rejected_even_for_unusable_future_row(bad_label):
    """Invalid rows must not be silently ignored by the PIT eligibility gate."""
    row = PITObservation(CUTOFF + timedelta(days=1), None, bad_label, None)
    with pytest.raises(TypeError, match="event labels must be bool or None"):
        pit_historical_prevalence([row], CUTOFF, horizon_days=30, target="growth")


def test_naive_decision_timestamp_rejected():
    row = PITObservation(datetime(2026, 10, 1), None, None, None)
    with pytest.raises(ValueError, match="timezone-aware"):
        pit_historical_prevalence([row], CUTOFF, horizon_days=14, target="downside")
