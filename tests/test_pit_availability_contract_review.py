"""Review (dialog 0460) of 8b57fd1: findings as strict xfail. Synthetic only."""
import pytest

from research.pit_availability_contract import (
    PITAvailabilityError, audit_event_availability,
)

ROW = {"event_id": "a", "publication_at": "2026-01-01T10:00:00Z",
       "observed_at": "2026-01-01T10:05:00Z"}


@pytest.mark.xfail(strict=True, reason="R1 MAJOR: agreed rule (Q16/0439, e344063) is strict observed < decision")
def test_same_instant_observation_rejected():
    with pytest.raises(PITAvailabilityError):
        audit_event_availability([ROW], "2026-01-01T10:05:00Z")


@pytest.mark.xfail(strict=True, reason="R2 MAJOR: one future row aborts whole feed; cannot act as a PIT filter")
def test_future_row_is_excluded_not_fatal():
    future = dict(ROW, event_id="b", publication_at="2026-01-02T00:00:00Z",
                  observed_at="2026-01-02T00:01:00Z")
    assert audit_event_availability([ROW, future], "2026-01-01T12:00:00Z") == ("a",)


def test_offset_equivalent_instant_currently_accepted():
    # documents current (non-strict) behaviour across offsets
    assert audit_event_availability([ROW], "2026-01-01T11:05:00+01:00") == ("a",)
