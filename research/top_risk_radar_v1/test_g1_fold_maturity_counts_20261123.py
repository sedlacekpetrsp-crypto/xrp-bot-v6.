"""Synthetic QA: G1 fold maturity counts come from canonical folds; no market data."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.g1_fold_maturity_counts import g1_fold_maturity_counts

UTC = timezone.utc


def _grid(start, days):
    return [start + timedelta(days=i) for i in range(days)]


def test_embargo_purge_is_counted_not_reported_as_usable():
    # 2025-12-20 label ends 2026-01-03, +14 d embargo > 2026-01-01 => purged for test year 2026
    decisions = _grid(datetime(2025, 12, 1, 0, 5, tzinfo=UTC), 40)
    c = g1_fold_maturity_counts(decisions, as_of=datetime(2026, 3, 1, tzinfo=UTC))[2026]
    assert c["train"] + c["purged_or_unmatured_train"] == 31
    # last usable train decision: d + 28 d <= 2026-01-01 => d <= 2025-12-04 00:00 -> 12-01..12-03 = 3
    assert c["train"] == 3
    assert c["test"] == 9 and c["excluded_unmatured_test"] == 0


def test_immature_test_rows_excluded_inclusive_boundary():
    decisions = _grid(datetime(2026, 1, 1, 0, 5, tzinfo=UTC), 3)
    as_of = decisions[1] + timedelta(days=14)
    c = g1_fold_maturity_counts(decisions, as_of=as_of)[2026]
    assert (c["test"], c["excluded_unmatured_test"]) == (2, 1)


def test_non_utc_offset_rejected_like_canonical():
    plus2 = timezone(timedelta(hours=2))
    d = [datetime(2026, 1, 1, 0, 5, tzinfo=UTC).astimezone(plus2)]
    with pytest.raises(ValueError):
        g1_fold_maturity_counts(d, as_of=datetime(2026, 3, 1, tzinfo=UTC))
