"""Synthetic cross-horizon temporal-isolation QA; no market data or performance runs.

The same decision timestamps must not make a 30-day growth label available
when a 14-day downside label has matured. Training must also be purged at
the start of each held-out calendar year.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.walkforward import expanding_calendar_folds


UTC = timezone.utc
D = timedelta(days=1)


def folds(decisions, horizon, as_of):
    return expanding_calendar_folds(
        decisions, label_horizon=horizon * D, as_of=as_of,
        first_train_year=2024, first_test_year=2025, last_test_year=2025,
    )[0]


def test_growth_and_downside_have_independent_label_maturity():
    as_of = datetime(2025, 2, 1, tzinfo=UTC)
    decisions = [
        datetime(2024, 12, 1, tzinfo=UTC),   # mature in both train sets
        datetime(2024, 12, 15, tzinfo=UTC),  # mature for 14d, not 30d at fold start
        datetime(2025, 1, 10, tzinfo=UTC),   # mature for 14d, not 30d at as_of
        datetime(2025, 1, 18, tzinfo=UTC),   # exactly mature for 14d
        datetime(2025, 1, 19, tzinfo=UTC),   # immature for both
    ]
    growth = folds(decisions, 30, as_of)
    downside = folds(decisions, 14, as_of)
    assert growth.train_indices == (0,)
    assert downside.train_indices == (0, 1)
    assert growth.test_indices == ()
    assert downside.test_indices == (2, 3)
    assert growth.excluded_unmatured == (2, 3, 4)
    assert downside.excluded_unmatured == (4,)


@pytest.mark.parametrize("horizon", [14, 30])
def test_fold_indices_do_not_depend_on_input_order(horizon):
    as_of = datetime(2025, 4, 1, tzinfo=UTC)
    decisions = [
        datetime(2024, 10, 1, tzinfo=UTC),
        datetime(2024, 12, 31, tzinfo=UTC),
        datetime(2025, 1, 2, tzinfo=UTC),
        datetime(2025, 3, 25, tzinfo=UTC),
    ]
    forward = folds(decisions, horizon, as_of)
    reversed_fold = folds(list(reversed(decisions)), horizon, as_of)
    assert {decisions[i] for i in forward.train_indices} == {
        list(reversed(decisions))[i] for i in reversed_fold.train_indices
    }
    assert {decisions[i] for i in forward.test_indices} == {
        list(reversed(decisions))[i] for i in reversed_fold.test_indices
    }
    assert {decisions[i] for i in forward.excluded_unmatured} == {
        list(reversed(decisions))[i] for i in reversed_fold.excluded_unmatured
    }


def test_exact_as_of_boundary_is_mature_and_next_instant_is_not():
    as_of = datetime(2025, 3, 1, tzinfo=UTC)
    exact = as_of - 30 * D
    later = exact + timedelta(microseconds=1)
    result = folds([exact, later], 30, as_of)
    assert result.test_indices == (0,)
    assert result.excluded_unmatured == (1,)
