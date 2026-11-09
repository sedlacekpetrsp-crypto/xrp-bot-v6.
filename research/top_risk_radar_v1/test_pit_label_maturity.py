"""PIT label-maturity invariants; synthetic data only, no backtest."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pit_prevalence import (
    PITObservation,
    pit_historical_prevalence,
)

CUTOFF = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_negative_label_cannot_be_available_before_horizon(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 5)
    premature = decision + timedelta(days=horizon) - timedelta(microseconds=1)
    row = PITObservation(
        decision, premature,
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    with pytest.raises(ValueError, match="negative label available before horizon"):
        pit_historical_prevalence([row], CUTOFF, horizon_days=horizon, target=target)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_negative_label_available_exactly_at_maturity_is_eligible(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 1)
    row = PITObservation(
        decision, decision + timedelta(days=horizon),
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    result = pit_historical_prevalence([row], CUTOFF, horizon_days=horizon, target=target)
    assert result == {"status": "descriptive_pit_baseline", "n": 1, "rate": 0.0}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_positive_label_can_be_published_on_early_hit(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 1)
    row = PITObservation(
        decision, decision + timedelta(hours=1),
        True if target == "growth" else None,
        True if target == "downside" else None,
    )
    result = pit_historical_prevalence([row], CUTOFF, horizon_days=horizon, target=target)
    assert result == {"status": "descriptive_pit_baseline", "n": 1, "rate": 1.0}


def test_unselected_label_does_not_impose_other_target_horizon():
    # Shared observation has a single timestamp; maturity is enforced only
    # for the selected target, not for an unrelated label.
    decision = CUTOFF - timedelta(days=31)
    row = PITObservation(decision, decision + timedelta(days=14), True, False)
    result = pit_historical_prevalence([row], CUTOFF, horizon_days=30, target="growth")
    assert result["n"] == 1
