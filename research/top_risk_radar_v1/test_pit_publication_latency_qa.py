"""Synthetic invariants for PIT baseline eligibility and publication latency.

Descriptive baseline only. These tests do NOT validate predictive performance.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pit_prevalence import PITObservation, pit_historical_prevalence


CUT = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
CASES = [("growth", 30), ("downside", 14)]


def row(decision, available, target, label):
    return PITObservation(
        decision, available,
        label if target == "growth" else None,
        label if target == "downside" else None,
    )


@pytest.mark.parametrize("target,horizon", CASES)
def test_late_published_negative_is_not_inferred_from_maturity(target, horizon):
    """A fully matured negative remains unknown until its publication."""
    decision = CUT - timedelta(days=horizon + 5)
    negative = row(decision, CUT + timedelta(microseconds=1), target, False)
    assert pit_historical_prevalence([negative], CUT, target=target, horizon_days=horizon) == {
        "status": "insufficient_train", "n": 0, "rate": None,
    }
    assert pit_historical_prevalence(
        [negative], CUT + timedelta(microseconds=1), target=target, horizon_days=horizon
    ) == {"status": "descriptive_pit_baseline", "n": 1, "rate": 0.0}


@pytest.mark.parametrize("target,horizon", CASES)
def test_target_without_its_own_label_never_borrows_other_target(target, horizon):
    decision = CUT - timedelta(days=40)
    other_only = PITObservation(
        decision, decision + timedelta(days=35),
        None if target == "growth" else True,
        True if target == "growth" else None,
    )
    assert pit_historical_prevalence(
        [other_only], CUT, target=target, horizon_days=horizon
    ) == {"status": "insufficient_train", "n": 0, "rate": None}


@pytest.mark.parametrize("target,horizon", CASES)
def test_adding_unavailable_rows_does_not_change_prevalence(target, horizon):
    decision = CUT - timedelta(days=horizon + 5)
    known = row(decision, CUT - timedelta(days=1), target, True)
    delayed = row(decision - timedelta(days=1), CUT + timedelta(days=1), target, False)
    unknown = row(decision - timedelta(days=2), None, target, False)
    baseline = pit_historical_prevalence([known], CUT, target=target, horizon_days=horizon)
    assert baseline == {"status": "descriptive_pit_baseline", "n": 1, "rate": 1.0}
    assert pit_historical_prevalence(
        [unknown, delayed, known], CUT, target=target, horizon_days=horizon
    ) == baseline


@pytest.mark.parametrize("target,horizon", CASES)
def test_future_cutoff_does_not_decrease_eligible_count(target, horizon):
    """Eligibility can grow with time, assuming a fixed valid row set."""
    decision = CUT - timedelta(days=horizon + 2)
    early = row(decision, CUT - timedelta(days=1), target, True)
    late = row(decision - timedelta(days=1), CUT + timedelta(days=1), target, False)
    at_cutoff = pit_historical_prevalence(
        [early, late], CUT, target=target, horizon_days=horizon
    )
    later = pit_historical_prevalence(
        [early, late], CUT + timedelta(days=2), target=target, horizon_days=horizon
    )
    assert at_cutoff["n"] == 1
    assert later["n"] == 2
    assert later["rate"] == 0.5
