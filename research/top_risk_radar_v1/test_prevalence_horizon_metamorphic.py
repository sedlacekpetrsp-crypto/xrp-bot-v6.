"""Synthetic invariants for descriptive XRP radar prevalence baselines.

No historical performance test, market download, or prediction evaluation.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.prevalence_baseline import Observation, historical_prevalence


CUT = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize("target", ["growth", "downside"])
def test_longer_horizon_cannot_increase_eligible_sample(target):
    rows = [
        Observation(CUT - timedelta(days=40), True, False),
        Observation(CUT - timedelta(days=30), False, True),
        Observation(CUT - timedelta(days=20), True, True),
        Observation(CUT - timedelta(days=14), False, False),
        Observation(CUT - timedelta(days=2), True, False),
    ]
    short = historical_prevalence(rows, CUT, horizon_days=14, target=target)
    long = historical_prevalence(rows, CUT, horizon_days=30, target=target)
    assert short["n"] == 4
    assert long["n"] == 2
    assert long["n"] <= short["n"]


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_unknown_labels_never_change_denominator_or_rate(target, horizon):
    known = [
        Observation(CUT - timedelta(days=40), True, False),
        Observation(CUT - timedelta(days=39), False, True),
    ]
    unknown = Observation(CUT - timedelta(days=38), None, None)
    original = historical_prevalence(known, CUT, horizon_days=horizon, target=target)
    with_unknown = historical_prevalence(known + [unknown], CUT, horizon_days=horizon, target=target)
    assert original == with_unknown


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_future_known_label_cannot_contaminate_training(target, horizon):
    eligible = Observation(CUT - timedelta(days=40), True, False)
    future = Observation(CUT + timedelta(days=1), False, True)
    baseline = historical_prevalence([eligible], CUT, horizon_days=horizon, target=target)
    assert historical_prevalence([eligible, future], CUT, horizon_days=horizon, target=target) == baseline


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_mature_boundary_is_inclusive_and_one_microsecond_early_is_not(target, horizon):
    mature = Observation(CUT - timedelta(days=horizon), True, False)
    immature = Observation(CUT - timedelta(days=horizon) + timedelta(microseconds=1), False, True)
    result = historical_prevalence([mature, immature], CUT, horizon_days=horizon, target=target)
    assert result["n"] == 1
    assert result["rate"] == (1.0 if target == "growth" else 0.0)
