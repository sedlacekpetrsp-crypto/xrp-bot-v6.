"""Synthetic-only G1 preflight composition regressions; no market data."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.g1_preflight import validated_g1_folds
from research.top_risk_radar_v1.g1_fold_contract import g1_calendar_folds

UTC = timezone.utc
AS_OF = datetime(2026, 11, 13, tzinfo=UTC)
START = datetime(2022, 1, 1, 0, 5, tzinfo=UTC)


def test_valid_grid_uses_fixed_embargoed_fold_contract():
    dates = [datetime(y, 1, 1, 0, 5, tzinfo=UTC) for y in range(2018, 2027)]
    assert validated_g1_folds(dates, as_of=AS_OF) == g1_calendar_folds(dates, as_of=AS_OF)


@pytest.mark.parametrize("dates", [
    [START, START],
    [START + timedelta(days=1), START],
    [START.replace(hour=1)],
    [START.replace(tzinfo=None)],
    [START.replace(tzinfo=timezone(timedelta(hours=1)))],
])
def test_invalid_grid_rejected_before_folds(dates):
    with pytest.raises(ValueError):
        validated_g1_folds(dates, as_of=AS_OF)


def test_missing_day_not_silently_filled():
    dates = [START, START + timedelta(days=2)]
    folds = validated_g1_folds(dates, as_of=AS_OF)
    fold = next(f for f in folds if f.test_year == 2022)
    assert fold.test_indices == (0, 1)
