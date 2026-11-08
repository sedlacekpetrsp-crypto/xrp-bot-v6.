"""Synthetic boundary and fail-closed QA for exposure eligibility (PAPER only).

No historical prices, performance backtest, or prediction evaluation.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.data_exposure import (
    Exposure,
    untouched_holdout,
    validate_exposures,
)

UTC = timezone.utc


def ts(day, hour=0):
    return datetime(2026, 1, day, hour, tzinfo=UTC)


def row(start, end, level="none"):
    return Exposure(start, end, level, "synthetic provenance")


@pytest.mark.parametrize("start,end", [
    (ts(1), ts(5)),  # uncovered prefix
    (ts(2), ts(6)),  # uncovered suffix
    (ts(1), ts(6)),  # both ends uncovered
])
def test_partial_coverage_cannot_be_called_untouched(start, end):
    assert not untouched_holdout([row(ts(2), ts(5))], start, end)


def test_adjacent_clean_intervals_cover_query_exactly():
    rows = [row(ts(1), ts(3)), row(ts(3), ts(5))]
    assert untouched_holdout(rows, ts(1), ts(5))


def test_one_second_gap_invalidates_entire_holdout():
    rows = [row(ts(1), ts(3)), row(ts(3) + timedelta(seconds=1), ts(5))]
    assert not untouched_holdout(rows, ts(1), ts(5))


def test_nonclean_interval_outside_requested_window_does_not_taint_it():
    rows = [row(ts(1), ts(3)), row(ts(3), ts(5), "tuned")]
    assert untouched_holdout(rows, ts(1), ts(3))


def test_nonclean_interval_inside_requested_window_taints_it():
    rows = [row(ts(1), ts(3)), row(ts(3), ts(5), "prevalence-viewed")]
    assert not untouched_holdout(rows, ts(1), ts(5))


def test_overlap_is_rejected_even_when_overlap_outside_requested_window():
    rows = [row(ts(1), ts(4)), row(ts(3), ts(5))]
    with pytest.raises(ValueError):
        untouched_holdout(rows, ts(1), ts(2))


def test_invalid_evidence_rejected_even_for_clean_period():
    with pytest.raises(ValueError):
        validate_exposures([Exposure(ts(1), ts(2), "none", "  ")])
