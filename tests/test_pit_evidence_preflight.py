import unittest
from research.pit_evidence_preflight import audit_evidence

DECISION = "2026-11-20T12:00:00Z"
BASE = {
    "source_id": "publisher-A", "event_id": "event-1",
    "archive_url": "https://web.archive.org/web/20261120100000/https://example.org/event",
    "published_at": "2026-11-20T09:00:00Z",
    "first_seen_at": "2026-11-20T10:00:00Z",
    "retrieved_at": "2026-11-20T11:00:00Z",
}


class PitEvidenceTests(unittest.TestCase):
    def test_valid_is_not_data_go(self):
        self.assertEqual(audit_evidence(BASE, DECISION)["status"], "PIT_EVIDENCE_PREFLIGHT_ONLY")

    def test_equal_decision_fails(self):
        self.assertEqual(audit_evidence({**BASE, "first_seen_at": DECISION}, DECISION)["status"], "DATA_NO_GO")

    def test_future_first_seen_fails(self):
        self.assertEqual(audit_evidence({**BASE, "first_seen_at": "2026-11-20T13:00:00Z"}, DECISION)["status"], "DATA_NO_GO")

    def test_future_publication_fails(self):
        self.assertEqual(audit_evidence({**BASE, "published_at": "2026-11-20T11:00:00Z"}, DECISION)["status"], "DATA_NO_GO")

    def test_naive_timestamp_fails(self):
        self.assertEqual(audit_evidence({**BASE, "published_at": "2026-11-20T09:00:00"}, DECISION)["status"], "DATA_NO_GO")

    def test_missing_archive_fails(self):
        self.assertEqual(audit_evidence({**BASE, "archive_url": "  "}, DECISION)["status"], "DATA_NO_GO")

    def test_non_string_id_fails(self):
        self.assertEqual(audit_evidence({**BASE, "event_id": True}, DECISION)["status"], "DATA_NO_GO")

    def test_insecure_url_fails(self):
        self.assertEqual(audit_evidence({**BASE, "archive_url": "http://example.org"}, DECISION)["status"], "DATA_NO_GO")

    def test_retrieval_before_first_seen_fails(self):
        self.assertEqual(audit_evidence({**BASE, "retrieved_at": "2026-11-20T08:00:00Z"}, DECISION)["status"], "DATA_NO_GO")

    def test_wayback_capture_after_first_seen_fails(self):
        row = {**BASE, "archive_url": "https://web.archive.org/web/20261120113000/https://example.org/event"}
        self.assertEqual(audit_evidence(row, DECISION)["reason"], "capture_after_claimed_first_seen")

    def test_wayback_invalid_capture_date_fails(self):
        row = {**BASE, "archive_url": "https://web.archive.org/web/20261320100000/https://example.org/event"}
        self.assertEqual(audit_evidence(row, DECISION)["reason"], "invalid_wayback_capture_timestamp")

    def test_wayback_missing_capture_fails(self):
        row = {**BASE, "archive_url": "https://web.archive.org/web/https://example.org/event"}
        self.assertEqual(audit_evidence(row, DECISION)["reason"], "invalid_wayback_capture_path")

    def test_bad_record_fails(self):
        self.assertEqual(audit_evidence(None, DECISION)["status"], "DATA_NO_GO")


if __name__ == "__main__":
    unittest.main()
