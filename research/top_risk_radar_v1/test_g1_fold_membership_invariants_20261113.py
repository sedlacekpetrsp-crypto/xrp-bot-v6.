"""Synthetic fold-membership invariants for Top Risk (14d) and Growth (30d).

No data access, fitting, predictions, or performance backtest. These tests
guard against reusing OOS decisions in train or evaluating immature labels.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.walkforward import expanding_calendar_folds


def utc(year, month=1, day=1, hour=0, minute=5):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize("days", [14, 30])
def test_all_fold_train_labels_end_before_test_start(days):
    horizon = timedelta(days=days)
    decisions = [
        utc(2017, 12, 31), utc(2018), utc(2021, 12, 1),
        utc(2021, 12, 31), utc(2022), utc(2022, 6, 1),
        utc(2023), utc(2024), utc(2025), utc(2026, 10, 1),
    ]
    cutoff = utc(2026, 11, 12)
    for fold in expanding_calendar_folds(decisions, label_horizon=horizon, as_of=cutoff):
        start = utc(fold.test_year, 1, 1, 0, 0)
        train = set(fold.train_indices)
        test = set(fold.test_indices)
        excluded = set(fold.excluded_unmatured)
        assert not (train & test or train & excluded or test & excluded)
        assert all(2018 <= decisions[i].year < fold.test_year for i in train)
        assert all(decisions[i] + horizon <= start for i in train)
        assert all(decisions[i] + horizon <= cutoff for i in train | test)
        assert all(decisions[i] + horizon > cutoff for i in excluded)
        assert all(decisions[i].year == fold.test_year for i in test | excluded)
        assert 0 not in train  # pre-2018 observations are never eligible


@pytest.mark.parametrize("days", [14, 30])
def test_fold_membership_is_invariant_to_input_permutation(days):
    decisions = [
        utc(2022, 1, 1), utc(2021, 11, 1), utc(2023, 6, 1),
        utc(2026, 11, 1), utc(2018, 5, 1), utc(2025, 2, 1),
    ]
    permuted = list(reversed(decisions))
    horizon = timedelta(days=days)
    kwargs = dict(label_horizon=horizon, as_of=utc(2026, 11, 12))
    original = expanding_calendar_folds(decisions, **kwargs)
    reversed_folds = expanding_calendar_folds(permuted, **kwargs)
    for left, right in zip(original, reversed_folds):
        assert left.test_year == right.test_year
        for attribute in ("train_indices", "test_indices", "excluded_unmatured"):
            left_times = {decisions[i] for i in getattr(left, attribute)}
            right_times = {permuted[i] for i in getattr(right, attribute)}
            assert left_times == right_times


@pytest.mark.parametrize("days", [14, 30])
def test_earlier_as_of_cannot_add_mature_test_rows(days):
    decisions = [utc(2026, 10, 1), utc(2026, 10, 20), utc(2026, 11, 1)]
    horizon = timedelta(days=days)
    earlier = expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=utc(2026, 11, 1)
    )[-1]
    later = expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=utc(2026, 12, 31)
    )[-1]
    assert set(earlier.test_indices) <= set(later.test_indices)
    assert set(later.excluded_unmatured) <= set(earlier.excluded_unmatured)


@pytest.mark.parametrize("days", [14, 30])
def test_exact_year_boundary_cannot_leak_future_decision_into_training(days):
    horizon = timedelta(days=days)
    start = utc(2024, 1, 1, 0, 0)
    decisions = [start - horizon, start - horizon + timedelta(microseconds=1), start]
    fold = next(f for f in expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=utc(2025, 1, 1)
    ) if f.test_year == 2024)
    assert fold.train_indices == (0,)
    assert fold.test_indices == (2,)
