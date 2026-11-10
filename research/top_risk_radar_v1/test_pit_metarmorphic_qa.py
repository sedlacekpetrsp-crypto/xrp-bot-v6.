"""Metamorphic QA for PIT descriptive prevalence; synthetic data only.

These checks do not estimate predictive skill or run performance backtests.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pit_prevalence import PITObservation, pit_historical_prevalence


CUTOFF = datetime(2026, 11, 10, tzinfo=timezone.utc)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_future_and_unpublished_rows_cannot_change_known_prevalence(target, horizon):
    known = PITObservation(
        CUTOFF - timedelta(days=horizon + 10),
        CUTOFF - timedelta(days=3),
        True if target == "growth" else None,
        True if target == "downside" else None,
    )
    future_decision = PITObservation(
        CUTOFF + timedelta(days=1),
        CUTOFF + timedelta(days=2),
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    unpublished = PITObservation(
        CUTOFF - timedelta(days=horizon + 4),
        CUTOFF + timedelta(seconds=1),
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    no_provenance = PITObservation(
        CUTOFF - timedelta(days=horizon + 2),
        None,
        False if target == "growth" else None,
        False if target == "downside" else None,
    )
    expected = {"status": "descriptive_pit_baseline", "n": 1, "rate": 1.0}
    for rows in ([known], [known, future_decision], [known, unpublished, no_provenance, future_decision],
                 [future_decision, no_provenance, known, unpublished]):
        assert pit_historical_prevalence(rows, CUTOFF, horizon_days=horizon, target=target) == expected


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_exact_publication_cutoff_included_but_one_microsecond_later_excluded(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 1)
    label = dict(growth=True if target == "growth" else None,
                 downside=True if target == "downside" else None)
    at_cutoff = PITObservation(decision, CUTOFF, **label)
    after_cutoff = PITObservation(decision, CUTOFF + timedelta(microseconds=1), **label)
    assert pit_historical_prevalence([at_cutoff], CUTOFF, horizon_days=horizon, target=target)["n"] == 1
    assert pit_historical_prevalence([after_cutoff], CUTOFF, horizon_days=horizon, target=target)["n"] == 0


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_rate_uses_only_eligible_denominator(target, horizon):
    labels = []
    for i, positive in enumerate([True, False, False, True]):
        decision = CUTOFF - timedelta(days=horizon + 10 + i)
        labels.append(PITObservation(
            decision, decision + timedelta(days=horizon),
            positive if target == "growth" else None,
            positive if target == "downside" else None,
        ))
    labels.append(PITObservation(
        CUTOFF - timedelta(days=horizon + 20), None,
        True if target == "growth" else None,
        True if target == "downside" else None,
    ))
    assert pit_historical_prevalence(labels, CUTOFF, horizon_days=horizon, target=target) == {
        "status": "descriptive_pit_baseline", "n": 4, "rate": 0.5
    }


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_same_instant_with_different_timezone_is_duplicate(target, horizon):
    decision = CUTOFF - timedelta(days=horizon + 2)
    row = PITObservation(decision, decision + timedelta(days=horizon), True, True)
    duplicate = PITObservation(
        decision.astimezone(timezone(timedelta(hours=5))),
        (decision + timedelta(days=horizon)).astimezone(timezone(timedelta(hours=5))),
        True, True,
    )
    with pytest.raises(ValueError, match="duplicate decision timestamp"):
        pit_historical_prevalence([row, duplicate], CUTOFF, horizon_days=horizon, target=target)
