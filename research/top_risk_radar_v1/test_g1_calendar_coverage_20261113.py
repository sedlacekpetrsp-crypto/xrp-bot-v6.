"""Synthetic G1 calendar completeness tests; no market data or backtest."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.g1_calendar_coverage import (
    missing_g1_decision_days,
    require_complete_g1_decision_days,
)

T = datetime(2024, 2, 28, 0, 5, tzinfo=timezone.utc)
DAY = timedelta(days=1)


def test_leap_day_gap_is_explicit_and_does_not_fill_data():
    observed = [T, T + 2 * DAY]
    assert missing_g1_decision_days(observed, start=T, end=T + 2 * DAY) == (T + DAY,)
    assert len(observed) == 2
    with pytest.raises(ValueError, match="1 missing UTC days"):
        require_complete_g1_decision_days(observed, start=T, end=T + 2 * DAY)


def test_complete_and_single_day_intervals_pass():
    complete = [T + i * DAY for i in range(3)]
    assert missing_g1_decision_days(complete, start=T, end=T + 2 * DAY) == ()
    require_complete_g1_decision_days(complete, start=T, end=T + 2 * DAY)
    require_complete_g1_decision_days([T], start=T, end=T)


@pytest.mark.parametrize("observed,start,end", [
    ([T - DAY, T], T, T + DAY),
    ([T + DAY, T], T, T + DAY),
    ([T, T], T, T + DAY),
    ([T], T + DAY, T),
    ([T], T.replace(hour=1), T),
    ([T.replace(tzinfo=None)], T, T),
])
def test_invalid_intervals_and_grid_fail_closed(observed, start, end):
    with pytest.raises(ValueError):
        missing_g1_decision_days(observed, start=start, end=end)


def test_empty_interval_is_reported_not_treated_as_success():
    assert missing_g1_decision_days([], start=T, end=T + DAY) == (T, T + DAY)
    with pytest.raises(ValueError, match="2 missing UTC days"):
        require_complete_g1_decision_days([], start=T, end=T + DAY)
