"""Synthetic chronology regression: no same-instant ingest allowed."""
from research.pit_event_order_gate import assess_event

BASE = {
    "event_id": "e1", "source_id": "official", "archive_id": "a1",
    "published_at": "2026-01-01T09:00:00Z",
    "first_seen_at": "2026-01-01T09:01:00Z",
    "effective_at": "2026-01-02T00:00:00Z",
}

def test_same_instant_rejected():
    assert assess_event(BASE, "2026-01-01T09:01:00Z") == {
        "status": "DATA_NO_GO", "reason": "not_known_at_decision"}

def test_capture_before_decision_only_time_pass():
    assert assess_event(BASE, "2026-01-01T09:01:01Z")["status"] == "PIT_TIME_PASS_ONLY"

def test_capture_after_decision_rejected():
    assert assess_event(BASE, "2026-01-01T09:00:59Z")["status"] == "DATA_NO_GO"

def test_timezone_equivalent_same_instant_rejected():
    assert assess_event(BASE, "2026-01-01T10:01:00+01:00")["status"] == "DATA_NO_GO"
