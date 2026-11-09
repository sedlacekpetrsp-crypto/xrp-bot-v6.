"""Synthetic datetime-extreme regressions for descriptive priors; PAPER only.

No historical prices, model fitting, or predictive OOS evaluation.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.prevalence_baseline import Observation, historical_prevalence


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_minimum_datetime_does_not_overflow_on_maturity_check(target, horizon):
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ancient = Observation(datetime.min.replace(tzinfo=timezone.utc), True, True)
    result = historical_prevalence([ancient], cutoff, horizon_days=horizon, target=target)
    assert result == {"status": "descriptive_baseline", "n": 1, "rate": 1.0}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_maximum_datetime_is_excluded_without_overflow(target, horizon):
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
    future = Observation(datetime.max.replace(tzinfo=timezone.utc), True, True)
    result = historical_prevalence([future], cutoff, horizon_days=horizon, target=target)
    assert result == {"status": "insufficient_train", "n": 0, "rate": None}
