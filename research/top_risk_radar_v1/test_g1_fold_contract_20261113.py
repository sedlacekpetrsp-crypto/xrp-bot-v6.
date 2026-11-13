"""Synthetic G1 contract tests; no performance run or market data."""
from datetime import datetime, timedelta, timezone

from research.top_risk_radar_v1.g1_fold_contract import (
    G1_EMBARGO, G1_HORIZON, g1_calendar_folds,
)
from research.top_risk_radar_v1.walkforward import expanding_calendar_folds

UTC = timezone.utc


def test_g1_embargo_is_mandatory_and_excludes_nearby_training_row():
    start = datetime(2022, 1, 1, tzinfo=UTC)
    decisions = [start - timedelta(days=28),
                 start - timedelta(days=27, seconds=1),
                 start + timedelta(days=1)]
    folds = g1_calendar_folds(decisions, as_of=datetime(2026, 11, 1, tzinfo=UTC))
    f = next(f for f in folds if f.test_year == 2022)
    assert G1_HORIZON == G1_EMBARGO == timedelta(days=14)
    assert f.train_indices == (0,)
    assert f.test_indices == (2,)


def test_g1_adapter_matches_explicit_safe_generic_configuration():
    dates = [datetime(y, 1, 1, tzinfo=UTC) for y in range(2018, 2027)]
    as_of = datetime(2026, 11, 1, tzinfo=UTC)
    actual = g1_calendar_folds(dates, as_of=as_of)
    expected = expanding_calendar_folds(
        dates, label_horizon=timedelta(days=14), embargo=timedelta(days=14),
        as_of=as_of, first_train_year=2018, first_test_year=2022, last_test_year=2026,
    )
    assert actual == expected


def test_g1_excludes_unmatured_latest_test_label():
    cutoff = datetime(2026, 11, 1, tzinfo=UTC)
    decisions = [cutoff - timedelta(days=14),
                 cutoff - timedelta(days=13, seconds=1)]
    f = next(f for f in g1_calendar_folds(decisions, as_of=cutoff)
             if f.test_year == 2026)
    assert f.test_indices == (0,)
    assert f.excluded_unmatured == (1,)
