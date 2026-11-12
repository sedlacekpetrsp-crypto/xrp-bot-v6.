"""G1 / Early Growth walk-forward PIT and maturity regression tests.

Synthetic calendar decisions only. Never fits a model or loads market data.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.walkforward import expanding_calendar_folds


def at(year, month=1, day=1, hour=0, minute=5):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize("horizon_days", [14, 30])
def test_exact_train_maturity_boundary_and_one_microsecond_later(horizon_days):
    start = at(2022, 1, 1, 0, 0)
    horizon = timedelta(days=horizon_days)
    decisions = [start - horizon, start - horizon + timedelta(microseconds=1), start]
    fold = expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=at(2023, 1, 1)
    )[0]
    assert fold.train_indices == (0,)
    assert fold.test_indices == (2,)


@pytest.mark.parametrize("horizon_days", [14, 30])
def test_positive_early_hit_does_not_override_full_horizon_train_gate(horizon_days):
    # Model input contains only decision timestamps: even if a positive hit was
    # observable immediately, an incomplete horizon cannot enter train.
    start = at(2022, 1, 1, 0, 0)
    decisions = [start - timedelta(days=1), start]
    fold = expanding_calendar_folds(
        decisions, label_horizon=timedelta(days=horizon_days), as_of=at(2023)
    )[0]
    assert fold.train_indices == ()
    assert fold.test_indices == (1,)


@pytest.mark.parametrize("horizon_days", [14, 30])
def test_test_sample_matures_at_as_of_inclusive(horizon_days):
    cutoff = at(2026, 11, 12)
    horizon = timedelta(days=horizon_days)
    decisions = [cutoff - horizon, cutoff - horizon + timedelta(microseconds=1)]
    fold = expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=cutoff
    )[-1]
    assert fold.test_indices == (0,)
    assert fold.excluded_unmatured == (1,)


@pytest.mark.parametrize("horizon_days", [14, 30])
def test_unsorted_input_indices_do_not_change_temporal_eligibility(horizon_days):
    decisions = [at(2022), at(2021, 1, 1), at(2026, 11, 1)]
    fold = expanding_calendar_folds(
        decisions, label_horizon=timedelta(days=horizon_days),
        as_of=at(2026, 11, 12)
    )[0]
    assert fold.train_indices == (1,)
    assert fold.test_indices == (0,)


def test_non_utc_offset_is_rejected_even_if_same_absolute_instant():
    offset = timezone(timedelta(hours=1))
    with pytest.raises(ValueError, match="UTC"):
        expanding_calendar_folds(
            [datetime(2022, 1, 1, 1, 5, tzinfo=offset)],
            label_horizon=timedelta(days=14), as_of=at(2023)
        )


def test_as_of_non_utc_offset_is_rejected():
    with pytest.raises(ValueError, match="UTC"):
        expanding_calendar_folds(
            [at(2022)], label_horizon=timedelta(days=14),
            as_of=datetime(2023, 1, 1, 1, tzinfo=timezone(timedelta(hours=1)))
        )
