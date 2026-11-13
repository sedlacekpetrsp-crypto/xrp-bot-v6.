"""Synthetic-only coverage-aware G1 preflight integration tests."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.g1_preflight import complete_g1_folds, validated_g1_folds

UTC = timezone.utc
D = timedelta(days=1)
START = datetime(2022, 1, 1, 0, 5, tzinfo=UTC)
AS_OF = datetime(2026, 11, 13, tzinfo=UTC)


def test_complete_grid_returns_identical_fixed_embargo_folds():
    decisions = [START + i * D for i in range(4)]
    assert complete_g1_folds(
        decisions, as_of=AS_OF, coverage_start=START,
        coverage_end=START + 3 * D,
    ) == validated_g1_folds(decisions, as_of=AS_OF)


@pytest.mark.parametrize("decisions,start,end", [
    ([START, START + 2 * D], START, START + 2 * D),  # internal gap
    ([START + D, START + 2 * D], START, START + 2 * D),  # leading gap
    ([START, START + D], START, START + 2 * D),  # trailing gap
    ([], START, START),  # no rows
])
def test_coverage_gaps_fail_closed(decisions, start, end):
    with pytest.raises(ValueError, match="coverage incomplete"):
        complete_g1_folds(
            decisions, as_of=AS_OF, coverage_start=start, coverage_end=end,
        )


def test_cannot_hide_trailing_gap_by_passing_row_derived_bounds():
    observed = [START, START + D]
    with pytest.raises(ValueError, match="coverage incomplete"):
        complete_g1_folds(
            observed, as_of=AS_OF, coverage_start=START,
            coverage_end=START + 2 * D,
        )


def test_invalid_coverage_bound_fails_before_fold_generation():
    with pytest.raises(ValueError):
        complete_g1_folds(
            [START], as_of=AS_OF,
            coverage_start=START.replace(hour=1), coverage_end=START,
        )
