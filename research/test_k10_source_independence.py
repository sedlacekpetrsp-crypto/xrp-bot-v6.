import unittest
from datetime import datetime, timezone, timedelta
from k10_source_independence import Evidence, assess
NOW = datetime(2023,1,1,tzinfo=timezone.utc)
def item(publisher="A",exchange="X",observed=NOW,url="https://source.example/label"):
    return Evidence("rAddress",exchange,publisher,url,observed,NOW)
class GateTests(unittest.TestCase):
    def test_empty(self): self.assertEqual(assess([])["reason"],"no_evidence")
    def test_mirrors(self): self.assertEqual(assess([item("A"),item("a",url="https://archive.example/snapshot")])["reason"],"insufficient_independent_publishers")
    def test_provisional(self): self.assertEqual(assess([item("A"),item("B")])["status"],"PROVISIONAL_PIT_ONLY")
    def test_conflict(self): self.assertEqual(assess([item("A"),item("B",exchange="Y")])["reason"],"conflicting_attribution")
    def test_future(self): self.assertEqual(assess([item("A"),item("B",observed=NOW+timedelta(seconds=1))])["reason"],"future_evidence")
    def test_naive(self):
        with self.assertRaises(ValueError): assess([item("A"),item("B",observed=datetime(2023,1,1))])
    def test_url(self): self.assertEqual(assess([item("A"),item("B",url="http://example.com")])["reason"],"invalid_original_url")
    def test_missing(self): self.assertEqual(assess([item(""),item("B")])["reason"],"missing_provenance")
    def test_threshold(self):
        with self.assertRaises(ValueError): assess([item("A")],1)
if __name__ == "__main__": unittest.main()
