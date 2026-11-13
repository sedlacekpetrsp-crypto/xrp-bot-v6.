"""Synthetic-only explicit embargo QA for both XRP PAPER radar horizons.

No market data, model fitting, predictions or performance execution.
"""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.walkforward import expanding_calendar_folds


START = datetime(2022, 1, 1, tzinfo=timezone.utc)
AS_OF = datetime(2023, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("horizon_days", [14, 30])
def test_14_day_embargo_excludes_mature_but_too_recent_train_label(horizon_days):
    horizon = timedelta(days=horizon_days)
    embargo = timedelta(days=14)
    decisions = [
        START - horizon - embargo,
        START - horizon - embargo + timedelta(microseconds=1),
        START - horizon,
        START,
    ]
    fold = expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=AS_OF,
        embargo=embargo,
    )[0]
    assert fold.train_indices == (0,)
    assert fold.test_indices == (3,)
    assert fold.excluded_unmatured == ()


@pytest.mark.parametrize("horizon_days", [14, 30])
def test_embargo_never_changes_test_label_maturity(horizon_days):
    horizon = timedelta(days=horizon_days)
    cutoff = datetime(2026, 11, 13, tzinfo=timezone.utc)
    decisions = [cutoff - horizon, cutoff - horizon + timedelta(microseconds=1)]
    fold = expanding_calendar_folds(
        decisions, label_horizon=horizon, as_of=cutoff,
        embargo=timedelta(days=14),
    )[-1]
    assert fold.test_indices == (0,)
    assert fold.excluded_unmatured == (1,)


def test_negative_embargo_is_rejected_fail_closed():
    with pytest.raises(ValueError, match="embargo"):
        expanding_calendar_folds(
            [START], label_horizon=timedelta(days=14), as_of=AS_OF,
            embargo=timedelta(microseconds=-1),
        )


def test_default_remains_backward_compatible_but_is_not_g1_compliant():
    # Existing callers retain their previous behavior. G1 MUST explicitly
    # pass timedelta(days=14), and the pre-run manifest must verify this.
    decision = START - timedelta(days=14)
    old = expanding_calendar_folds(
        [decision], label_horizon=timedelta(days=14), as_of=AS_OF,
    )[0]
    gated = expanding_calendar_folds(
        [decision], label_horizon=timedelta(days=14), as_of=AS_OF,
        embargo=timedelta(days=14),
    )[0]
    assert old.train_indices == (0,)
    assert gated.train_indices == ()
