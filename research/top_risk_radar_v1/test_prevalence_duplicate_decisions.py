"""Synthetic QA: duplicate timestamps must not bias historical prevalence.

No market data, performance backtest, or OOS predictions are involved.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.prevalence_baseline import Observation, historical_prevalence


CUT = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_duplicate_mature_decision_is_rejected(target, horizon):
    at = CUT - timedelta(days=horizon + 2)
    rows = [Observation(at, True, False), Observation(at, False, True)]
    with pytest.raises(ValueError, match="duplicate decision timestamp"):
        historical_prevalence(rows, CUT, horizon_days=horizon, target=target)


def test_duplicate_with_different_timezone_offset_is_rejected():
    at = CUT - timedelta(days=40)
    same_instant = at.astimezone(timezone(timedelta(hours=5, minutes=30)))
    rows = [Observation(at, True, None), Observation(same_instant, False, None)]
    with pytest.raises(ValueError, match="duplicate decision timestamp"):
        historical_prevalence(rows, CUT, horizon_days=30, target="growth")


def test_duplicate_immature_or_unknown_rows_are_also_rejected():
    at = CUT - timedelta(days=2)
    rows = [Observation(at, None, None), Observation(at, None, None)]
    with pytest.raises(ValueError, match="duplicate decision timestamp"):
        historical_prevalence(rows, CUT, horizon_days=14, target="downside")


def test_distinct_decisions_remain_valid():
    rows = [
        Observation(CUT - timedelta(days=40), True, False),
        Observation(CUT - timedelta(days=39), False, True),
    ]
    result = historical_prevalence(rows, CUT, horizon_days=30, target="growth")
    assert result == {"status": "descriptive_baseline", "n": 2, "rate": 0.5}
