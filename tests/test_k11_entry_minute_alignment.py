"""Regression tests for K11 entry-aligned 60-minute perp availability.

Synthetic timestamps only; no market data or performance computation.
"""
from datetime import datetime, timedelta, timezone

from research.k11_step0_collector import _minute, perp_and_coverage


def _case(minute=37):
    announced = datetime(2026, 6, 10, 11, minute, tzinfo=timezone.utc)
    entry = announced + timedelta(minutes=60)
    # Synthetic 21-day continuous coverage; no price data.
    start = _minute(announced - timedelta(days=7))
    end = _minute(announced + timedelta(days=14))
    return announced, entry, set(range(start, end))


def test_missing_minute_after_hour_boundary_rejects_entry_window():
    announced, entry, minutes = _case()
    minutes.remove(_minute(entry + timedelta(minutes=30)))
    perp_ok, coverage_ok, _ = perp_and_coverage(minutes, announced)
    assert not perp_ok
    assert coverage_ok  # 1 missing minute does not fail 95% coverage


def test_missing_minute_before_entry_does_not_reject_entry_window():
    announced, entry, minutes = _case()
    minutes.remove(_minute(entry - timedelta(minutes=1)))
    perp_ok, coverage_ok, _ = perp_and_coverage(minutes, announced)
    assert perp_ok
    assert coverage_ok


def test_aligned_entry_full_hour_passes():
    announced, _, minutes = _case(minute=0)
    assert perp_and_coverage(minutes, announced)[0]


def test_missing_exact_entry_minute_rejects():
    announced, entry, minutes = _case()
    minutes.remove(_minute(entry))
    assert not perp_and_coverage(minutes, announced)[0]


def test_missing_last_required_minute_rejects():
    announced, entry, minutes = _case()
    minutes.remove(_minute(entry + timedelta(minutes=59)))
    assert not perp_and_coverage(minutes, announced)[0]


def test_missing_first_minute_after_required_hour_does_not_reject():
    announced, entry, minutes = _case()
    minutes.remove(_minute(entry + timedelta(minutes=60)))
    assert perp_and_coverage(minutes, announced)[0]
