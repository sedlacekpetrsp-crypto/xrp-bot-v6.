import pandas as pd
import pytest

from research.k9_round_number.hour_boundary_audit import hour_candidate_positions


def test_partial_first_hour_has_controls_even_without_hour_floor_row():
    idx = pd.date_range("2026-01-01 12:20", periods=100, freq="min", tz="UTC")
    got = hour_candidate_positions(idx, idx[10], 15)
    assert 0 in got
    assert 10 not in got
    assert all(idx[i].hour == 12 for i in got)


def test_controls_never_cross_hour_or_incomplete_horizon():
    idx = pd.date_range("2026-01-01 12:20", periods=45, freq="min", tz="UTC")
    got = hour_candidate_positions(idx, idx[20], 15)
    assert all(idx[i].hour == 12 and i + 15 < len(idx) for i in got)


def test_gap_in_horizon_excludes_control():
    idx = pd.date_range("2026-01-01 12:00", periods=90, freq="min", tz="UTC")
    idx = idx.delete(12)
    got = hour_candidate_positions(idx, idx[3], 15)
    assert 2 not in got
    assert 3 not in got


@pytest.mark.parametrize("bad", [
    pd.DatetimeIndex(["2026-01-01 12:00", "2026-01-01 12:01"]),
    pd.DatetimeIndex(["2026-01-01 12:01Z", "2026-01-01 12:00Z"]),
    pd.DatetimeIndex(["2026-01-01 12:00Z", "2026-01-01 12:00Z"]),
])
def test_bad_index_fails_closed(bad):
    with pytest.raises(ValueError):
        hour_candidate_positions(bad, pd.Timestamp("2026-01-01 12:00Z"), 15)


def test_naive_signal_rejected():
    idx = pd.date_range("2026-01-01 12:00", periods=60, freq="min", tz="UTC")
    with pytest.raises(ValueError):
        hour_candidate_positions(idx, pd.Timestamp("2026-01-01 12:05"), 15)
