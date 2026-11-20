"""Claude review of K13 announcement gate 7c6c66e (dialog 0421). Synthetic only; no prices, no performance.

Strict xfail = confirmed defect; the fix should make the test pass (then remove xfail)."""
import unittest
from research.k13_announcement_gate import article_gate, feasibility

BASE = dict(code="A", title="Changes to Leverage and Margin Tiers", release_at="2024-01-01T00:00:00Z",
            capture_at="2024-01-01T06:00:00Z", effective_at="2024-01-02T00:00:00Z",
            status=200, text="XRPUSDT Tier 1 5%")


class TestK13GateReview(unittest.TestCase):
    def test_baseline_still_ok(self):
        self.assertTrue(article_gate(BASE)["ok"])

    @unittest.expectedFailure
    def test_k1_tier_number_alone_is_not_tier_evidence(self):
        # NUMBER also matches the "1" in "Tier 1" => the numeric check is vacuous.
        self.assertFalse(article_gate({**BASE, "text": "XRPUSDT Tier 1"})["ok"])

    @unittest.expectedFailure
    def test_k2_non_target_articles_must_not_consume_sample_slots(self):
        target = [{**BASE, "code": f"t{i}"} for i in range(20)]
        other = [{**BASE, "code": f"n{i}", "title": "Binance Will List FOO"} for i in range(20)]
        self.assertEqual(feasibility(target + other)["status"], feasibility(target)["status"])

    @unittest.expectedFailure
    def test_k3_protocol_event_floor_ge_60_is_enforced(self):
        # 0420 protocol: GO <=> >=10/20 PIT_OK AND >=60 events. 20 articles cannot prove >=60 events.
        res = feasibility([{**BASE, "code": f"t{i}"} for i in range(20)])
        self.assertIn("n_events", res)

    @unittest.expectedFailure
    def test_k4_capture_without_provenance_fails_closed(self):
        # No source URL / SHA-256 of the captured body => the PIT claim is not auditable.
        self.assertEqual(article_gate(BASE)["reason"], "missing_provenance")


if __name__ == "__main__":
    unittest.main()
