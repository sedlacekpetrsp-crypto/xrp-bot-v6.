import unittest
from research.k13_announcement_gate import article_gate, feasibility

BASE = dict(code="A", title="Changes to Leverage and Margin Tiers", release_at="2024-01-01T00:00:00Z",
            capture_at="2024-01-01T06:00:00Z", effective_at="2024-01-02T00:00:00Z",
            status=200, text="XRPUSDT Tier 1 5%")

class TestK13(unittest.TestCase):
    def test_valid(self): self.assertTrue(article_gate(BASE)["ok"])
    def test_missing(self): self.assertFalse(article_gate({})["ok"])
    def test_bad_shape(self): self.assertFalse(article_gate(None)["ok"])
    def test_late_capture(self):
        self.assertEqual(article_gate({**BASE,"capture_at":"2024-01-03T00:00:00Z"})["reason"],"capture_outside_window")
    def test_capture_before_release(self):
        self.assertFalse(article_gate({**BASE,"capture_at":"2023-12-31T23:59:59Z"})["ok"])
    def test_naive(self):
        self.assertEqual(article_gate({**BASE,"release_at":"2024-01-01T00:00:00"})["reason"],"bad_timestamp")
    def test_status(self): self.assertFalse(article_gate({**BASE,"status":404})["ok"])
    def test_no_symbol(self): self.assertFalse(article_gate({**BASE,"text":"Tier 1 5%"})["ok"])
    def test_no_tier(self): self.assertFalse(article_gate({**BASE,"text":"XRPUSDT 5%"})["ok"])
    def test_effective_before_release(self):
        self.assertFalse(article_gate({**BASE,"effective_at":"2023-12-01T00:00:00Z"})["ok"])
    def test_insufficient_sample(self):
        self.assertEqual(feasibility([BASE])["status"],"DATA_NO_GO")
    def test_twenty(self):
        a=[{**BASE,"code":str(i)} for i in range(20)]
        self.assertEqual(feasibility(a)["status"],"DATA_FEASIBLE_SAMPLE")
    def test_conflicting_duplicate(self):
        with self.assertRaises(ValueError): feasibility([BASE,{**BASE,"title":"changed"}])
    def test_identical_duplicate(self):
        self.assertEqual(feasibility([BASE,BASE])["sample_size"],1)

if __name__ == "__main__": unittest.main()
