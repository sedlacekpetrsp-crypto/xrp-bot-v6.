"""Synthetic guard against positive-event ascertainment bias in descriptive PIT baselines.

A positive hit can be observed early, but the denominator must consist of
fully matured decision windows; otherwise early winners inflate prevalence.
This is NOT a predictive/OOS validation or a performance backtest.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pit_prevalence import PITObservation, pit_historical_prevalence

CUT = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_early_positive_in_unmatured_window_does_not_bias_rate(target, horizon):
    mature_decision = CUT - timedelta(days=horizon + 2)
    young_decision = CUT - timedelta(days=horizon - 1)
    negative = PITObservation(
        mature_decision, mature_decision + timedelta(days=horizon),
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    early_hit = PITObservation(
        young_decision, young_decision + timedelta(hours=1),
        True if target == "growth" else None,
        True if target == "downside" else None,
    )
    assert pit_historical_prevalence(
        [negative, early_hit], CUT, horizon_days=horizon, target=target
    ) == {"status": "descriptive_pit_baseline", "n": 1, "rate": 0.0}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_only_early_positive_yields_insufficient_mature_training(target, horizon):
    decision = CUT - timedelta(days=horizon - 1)
    row = PITObservation(
        decision, decision + timedelta(hours=1),
        True if target == "growth" else None,
        True if target == "downside" else None,
    )
    assert pit_historical_prevalence(
        [row], CUT, horizon_days=horizon, target=target
    ) == {"status": "insufficient_train", "n": 0, "rate": None}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_positive_at_exact_maturity_enters_denominator(target, horizon):
    decision = CUT - timedelta(days=horizon)
    row = PITObservation(
        decision, decision + timedelta(hours=1),
        True if target == "growth" else None,
        True if target == "downside" else None,
    )
    assert pit_historical_prevalence(
        [row], CUT, horizon_days=horizon, target=target
    ) == {"status": "descriptive_pit_baseline", "n": 1, "rate": 1.0}
