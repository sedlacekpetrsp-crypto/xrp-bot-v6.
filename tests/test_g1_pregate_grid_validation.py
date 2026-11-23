"""Synthetic fail-closed validation for G1 decision grids; no market data or performance."""
from datetime import datetime, timedelta, timezone
import pytest
from research.top_risk_radar_v1.g1_power_pregate import labels_fingerprint

T0 = datetime(2022, 1, 1, tzinfo=timezone.utc)

def test_reject_duplicate_decisions():
    with pytest.raises(ValueError, match="strictly increasing"):
        labels_fingerprint([T0, T0], [True, False])

def test_reject_reverse_order():
    with pytest.raises(ValueError, match="strictly increasing"):
        labels_fingerprint([T0 + timedelta(days=1), T0], [True, False])

def test_reject_naive_decisions():
    with pytest.raises(ValueError, match="timezone-aware"):
        labels_fingerprint([datetime(2022, 1, 1)], [True])

def test_reject_non_datetime():
    with pytest.raises(ValueError, match="datetime"):
        labels_fingerprint(["2022-01-01"], [True])

def test_valid_aware_grid_is_stable():
    grid = [T0, T0 + timedelta(days=1)]
    assert labels_fingerprint(grid, [True, None]) == labels_fingerprint(grid, [True, None])
