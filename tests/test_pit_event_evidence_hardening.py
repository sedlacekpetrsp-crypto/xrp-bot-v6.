"""Synthetic-only regression checks for PIT chronology evidence guard."""
from research.pit_event_order_gate import assess_event


BASE = {
    "event_id": "E1", "source_id": "official", "archive_id": "capture-1",
    "published_at": "2026-01-01T10:00:00Z",
    "first_seen_at": "2026-01-01T10:05:00Z",
    "effective_at": "2026-01-02T00:00:00Z",
}
DECISION = "2026-01-01T10:06:00Z"


def test_valid_chronology_only_not_data_go():
    assert assess_event(BASE, DECISION)["status"] == "PIT_TIME_PASS_ONLY"


def test_blank_identifier_fails_closed():
    for key in ("event_id", "source_id", "archive_id"):
        event = {**BASE, key: "  "}
        assert assess_event(event, DECISION) == {
            "status": "DATA_NO_GO", "reason": "missing_evidence"}


def test_non_string_identifier_fails_closed():
    for value in (42, True, ["archive"], {"id": "archive"}):
        event = {**BASE, "archive_id": value}
        assert assess_event(event, DECISION)["status"] == "DATA_NO_GO"


def test_whitespace_timestamp_fails_closed():
    event = {**BASE, "published_at": "  "}
    assert assess_event(event, DECISION)["status"] == "DATA_NO_GO"


def test_unverified_future_capture_fails_closed():
    event = {**BASE, "first_seen_at": "2026-01-01T10:07:00Z"}
    assert assess_event(event, DECISION)["reason"] == "not_known_at_decision"


def test_publication_after_capture_fails_closed():
    event = {**BASE, "published_at": "2026-01-01T10:06:00Z"}
    assert assess_event(event, DECISION)["reason"] == "publication_after_capture"


def test_naive_decision_fails_closed():
    assert assess_event(BASE, "2026-01-01T10:06:00")["status"] == "DATA_NO_GO"
