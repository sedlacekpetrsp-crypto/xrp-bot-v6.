"""Synthetic fail-closed validation for G1 decision grids; no market data or performance."""
from datetime import datetime, timedelta, timezone
import pytest
from research.top_risk_radar_v1.g1_power_pregate import labels_fingerprint

T0 = datetime(2022, 1, 1, 0, 5, tzinfo=timezone.utc)

def test_reject_duplicate_decisions():
    with pytest.raises(ValueError, match="duplicate or out of order"):
        labels_fingerprint([T0, T0], [True, False])

def test_reject_reverse_order():
    with pytest.raises(ValueError, match="duplicate or out of order"):
        labels_fingerprint([T0 + timedelta(days=1), T0], [True, False])

def test_reject_naive_decisions():
    with pytest.raises(ValueError, match="must be UTC"):
        labels_fingerprint([datetime(2022, 1, 1)], [True])

def test_reject_non_datetime():
    with pytest.raises(ValueError, match="must be a datetime"):
        labels_fingerprint(["2022-01-01"], [True])

def test_valid_aware_grid_is_stable():
    grid = [T0, T0 + timedelta(days=1)]
    assert labels_fingerprint(grid, [True, None]) == labels_fingerprint(grid, [True, None])

def test_reject_non_utc_offset_same_instant():
    # same instant in +01:00 would otherwise hash differently (Claude review 2026-11-23)
    plus1 = T0.astimezone(timezone(timedelta(hours=1)))
    with pytest.raises(ValueError, match="must be UTC"):
        labels_fingerprint([plus1], [True])

def test_reject_off_grid_time():
    with pytest.raises(ValueError, match="00:05:00"):
        labels_fingerprint([datetime(2022, 1, 1, 13, 0, tzinfo=timezone.utc)], [True])
