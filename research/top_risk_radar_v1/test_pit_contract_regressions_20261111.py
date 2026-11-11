"""Deterministic PIT contract regressions; no network, model fit or backtest.

These tests are intentionally synthetic and fail closed on malformed provenance.
"""
import pytest

from research.top_risk_radar_v1.pit_guard import (
    feature_is_available,
    label_is_mature,
    parse_utc,
)


DECISION = "2026-11-11T00:05:00Z"


def record(**overrides):
    values = {
        "event_time": "2026-11-10T23:59:59Z",
        "source_published_at": "2026-11-11T00:04:59Z",
        "collector_received_at": "2026-11-11T00:04:59Z",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize("field", [
    "event_time", "source_published_at", "collector_received_at",
])
def test_missing_provenance_fails_closed(field):
    candidate = record()
    del candidate[field]
    with pytest.raises((KeyError, ValueError, TypeError)):
        feature_is_available(candidate, DECISION)


@pytest.mark.parametrize("field", [
    "event_time", "source_published_at", "collector_received_at",
])
def test_naive_provenance_fails_closed(field):
    with pytest.raises(ValueError, match="naive"):
        feature_is_available(record(**{field: "2026-11-11T00:00:00"}), DECISION)


def test_event_at_decision_forbidden_even_if_published_earlier():
    assert not feature_is_available(record(event_time=DECISION), DECISION)


def test_receipt_one_microsecond_after_decision_forbidden():
    assert not feature_is_available(
        record(collector_received_at="2026-11-11T00:05:00.000001Z"),
        DECISION,
    )


def test_publication_at_decision_allowed_for_past_event():
    assert feature_is_available(
        record(source_published_at=DECISION, collector_received_at=DECISION),
        DECISION,
    )


def test_offset_normalization_preserves_exact_instant():
    assert parse_utc("2026-11-11T01:05:00+01:00") == parse_utc(DECISION)
    assert feature_is_available(record(), "2026-11-11T01:05:00+01:00")


@pytest.mark.parametrize("horizon", [336, 720])
def test_label_maturity_exact_boundary_and_microsecond_before(horizon):
    from datetime import timedelta

    decision = parse_utc(DECISION)
    end = decision + timedelta(hours=horizon)
    assert label_is_mature(DECISION, end.isoformat(), horizon)
    assert not label_is_mature(
        DECISION, (end - timedelta(microseconds=1)).isoformat(), horizon
    )


@pytest.mark.parametrize("invalid", [True, False, 0, -1, 3.5, "336", None])
def test_invalid_horizon_rejected(invalid):
    with pytest.raises(ValueError):
        label_is_mature(DECISION, "2026-12-31T00:00:00Z", invalid)
