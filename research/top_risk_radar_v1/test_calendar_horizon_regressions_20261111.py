"""Calendar-boundary PIT regressions for both XRP radars (synthetic, PAPER only).

No market data, model training, performance evaluation or network access.
The horizons are fixed elapsed UTC hours, not local calendar months/days.
"""
from datetime import timedelta

import pytest

from research.top_risk_radar_v1.pit_guard import (
    feature_is_available,
    label_is_mature,
    parse_utc,
)


@pytest.mark.parametrize(
    ("decision", "horizon"),
    [
        ("2024-02-28T00:05:00Z", 720),  # Leap day inside 30-day horizon.
        ("2026-03-29T00:05:00Z", 336),  # EU spring DST transition.
        ("2026-10-25T00:05:00Z", 720),  # EU autumn DST transition.
    ],
)
def test_horizon_uses_elapsed_utc_hours_across_calendar_changes(decision, horizon):
    exact_end = parse_utc(decision) + timedelta(hours=horizon)
    assert label_is_mature(decision, exact_end.isoformat(), horizon)
    assert not label_is_mature(
        decision, (exact_end - timedelta(microseconds=1)).isoformat(), horizon
    )


def test_same_instant_in_different_offsets_does_not_create_early_maturity():
    decision = "2026-03-29T01:05:00+01:00"
    cutoff_utc = parse_utc(decision) + timedelta(hours=336)
    assert label_is_mature(decision, cutoff_utc.isoformat(), 336)
    assert not label_is_mature(
        decision,
        (cutoff_utc - timedelta(seconds=1)).astimezone().isoformat(),
        336,
    )


def test_publication_timezone_offset_cannot_hide_post_decision_timestamp():
    decision = "2026-10-25T00:05:00Z"
    record = {
        "event_time": "2026-10-24T23:59:59Z",
        "source_published_at": "2026-10-25T02:05:00.000001+02:00",
        "collector_received_at": "2026-10-25T00:04:59Z",
    }
    assert not feature_is_available(record, decision)


def test_leap_day_event_at_decision_is_not_historical():
    decision = "2024-02-29T00:05:00Z"
    record = {
        "event_time": "2024-02-29T01:05:00+01:00",
        "source_published_at": "2024-02-29T00:04:59Z",
        "collector_received_at": "2024-02-29T00:04:59Z",
    }
    assert not feature_is_available(record, decision)
