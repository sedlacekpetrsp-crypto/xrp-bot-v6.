"""Metamorphic PIT invariants for descriptive XRP radar baselines.

Synthetic observations only; no historical outcomes or predictive performance.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pit_prevalence import PITObservation, pit_historical_prevalence


CUTOFF = datetime(2026, 11, 10, tzinfo=timezone.utc)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_future_rows_cannot_change_mature_baseline(target, horizon):
    past = CUTOFF - timedelta(days=horizon + 10)
    known = PITObservation(
        past, past + timedelta(days=horizon),
        True if target == "growth" else None,
        True if target == "downside" else None,
    )
    future = PITObservation(
        CUTOFF + timedelta(days=1), None,
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    expected = {"status": "descriptive_pit_baseline", "n": 1, "rate": 1.0}
    assert pit_historical_prevalence([known], CUTOFF, horizon_days=horizon, target=target) == expected
    assert pit_historical_prevalence([future, known], CUTOFF, horizon_days=horizon, target=target) == expected


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_same_instant_in_different_timezones_is_duplicate(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 3)
    available = decision + timedelta(days=horizon)
    first = PITObservation(decision, available, False, False)
    offset = timezone(timedelta(hours=5, minutes=30))
    second = PITObservation(decision.astimezone(offset), available.astimezone(offset), False, False)
    with pytest.raises(ValueError, match="duplicate decision timestamp"):
        pit_historical_prevalence([first, second], CUTOFF, horizon_days=horizon, target=target)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_unavailable_labels_do_not_change_denominator(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 5)
    known = PITObservation(decision, decision + timedelta(days=horizon), False, False)
    unknown = PITObservation(decision - timedelta(days=1), None, True, True)
    assert pit_historical_prevalence(
        [known, unknown], CUTOFF, horizon_days=horizon, target=target
    ) == {"status": "descriptive_pit_baseline", "n": 1, "rate": 0.0}
