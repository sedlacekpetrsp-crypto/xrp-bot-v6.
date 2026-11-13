"""Synthetic-only G1 decision-grid QA. No prediction, market data or backtest."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.g1_decision_input import validate_g1_decisions

UTC = timezone.utc
T = datetime(2024, 2, 28, 0, 5, tzinfo=UTC)


def test_valid_leap_day_and_missing_day_allowed_for_separate_coverage_audit():
    validate_g1_decisions([T, T + timedelta(days=1), T + timedelta(days=3)])
    validate_g1_decisions([])


@pytest.mark.parametrize("bad", [
    T.replace(tzinfo=None),
    T.replace(tzinfo=timezone(timedelta(hours=1))),
    T.replace(hour=1),
    T.replace(minute=4),
    T.replace(second=1),
    T.replace(microsecond=1),
    "2024-02-28T00:05:00Z",
])
def test_reject_noncanonical_decision(bad):
    with pytest.raises(ValueError):
        validate_g1_decisions([bad])


@pytest.mark.parametrize("rows", [[T, T], [T + timedelta(days=1), T],
                                  [T, T + timedelta(microseconds=1)]])
def test_reject_duplicate_reversed_or_non_grid_rows(rows):
    with pytest.raises(ValueError):
        validate_g1_decisions(rows)
