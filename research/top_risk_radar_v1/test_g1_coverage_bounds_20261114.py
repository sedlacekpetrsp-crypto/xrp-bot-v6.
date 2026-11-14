"""Synthetic-only regression tests: invalid G1 coverage bounds fail closed."""
from datetime import datetime, timezone

import pytest

from research.top_risk_radar_v1.g1_calendar_coverage import missing_g1_decision_days

START = datetime(2022, 1, 1, 0, 5, tzinfo=timezone.utc)
END = datetime(2022, 1, 2, 0, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("start,end", [
    (START.replace(tzinfo=None), END),
    (START, END.replace(tzinfo=None)),
    (START, "2022-01-02T00:05:00Z"),
    ("2022-01-01T00:05:00Z", END),
])
def test_invalid_bounds_raise_controlled_value_error(start, end):
    with pytest.raises(ValueError, match="must be (UTC|a datetime)"):
        missing_g1_decision_days([START, END], start=start, end=end)


def test_reverse_valid_bounds_are_rejected():
    with pytest.raises(ValueError, match="end precedes start"):
        missing_g1_decision_days([START, END], start=END, end=START)


def test_valid_bounds_preserve_complete_grid():
    assert missing_g1_decision_days([START, END], start=START, end=END) == ()
