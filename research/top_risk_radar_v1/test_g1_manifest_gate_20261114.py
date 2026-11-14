import unittest

from research.top_risk_radar_v1.g1_manifest_gate import g1_manifest_readiness_issues
from research.top_risk_radar_v1.test_source_manifest import GOOD


class G1ManifestReadinessTests(unittest.TestCase):
    def test_verified_pit_manifest_passes_metadata_gate(self):
        record = {**GOOD, "qa_status": "verified"}
        self.assertEqual(g1_manifest_readiness_issues(record), [])

    def test_pending_or_rejected_source_fails_closed(self):
        for status in ("pending", "rejected"):
            with self.subTest(status=status):
                record = {**GOOD, "qa_status": status}
                self.assertIn("source_not_verified", g1_manifest_readiness_issues(record))

    def test_pit_unsupported_fails_closed(self):
        record = {**GOOD, "qa_status": "verified", "point_in_time_supported": False}
        self.assertIn("pit_not_supported", g1_manifest_readiness_issues(record))

    def test_invalid_metadata_cannot_pass_as_verified(self):
        record = {**GOOD, "qa_status": "verified", "raw_sha256": "bad"}
        self.assertIn("invalid_sha256", g1_manifest_readiness_issues(record))

    def test_nonboolean_pit_flag_fails_closed(self):
        record = {**GOOD, "qa_status": "verified", "point_in_time_supported": 1}
        self.assertIn("invalid_pit_flag", g1_manifest_readiness_issues(record))
