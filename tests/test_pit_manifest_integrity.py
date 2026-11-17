import hashlib
import tempfile
import unittest
from pathlib import Path
from research.pit_manifest_integrity import verify

class TestManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sample.csv").write_bytes(b"time,value\\n")
        self.item = dict(path="sample.csv", event_at="2026-01-01T00:00:00Z",
                         known_at="2026-01-01T01:00:00Z",
                         sha256=hashlib.sha256(b"time,value\\n").hexdigest())
    def tearDown(self): self.tmp.cleanup()
    def check(self, item=None, cutoff="2026-01-02T00:00:00Z"):
        return verify({"inputs": [item or self.item]}, self.root, cutoff)
    def test_valid(self): self.assertEqual(self.check()["status"], "PASS")
    def test_future_known(self):
        with self.assertRaises(ValueError): self.check(cutoff="2026-01-01T00:30:00Z")
    def test_hash(self):
        with self.assertRaises(ValueError): self.check({**self.item, "sha256": "0"*64})
    def test_escape(self):
        with self.assertRaises(ValueError): self.check({**self.item, "path": "../escape.csv"})
    def test_naive(self):
        with self.assertRaises(ValueError): self.check({**self.item, "known_at": "2026-01-01T01:00:00"})
    def test_event(self):
        with self.assertRaises(ValueError): self.check({**self.item, "event_at": "2026-01-03T00:00:00Z"})
    def test_duplicate(self):
        with self.assertRaises(ValueError): verify({"inputs":[self.item,self.item]},self.root,"2026-01-02T00:00:00Z")
    def test_empty(self):
        with self.assertRaises(ValueError): verify({"inputs":[]},self.root,"2026-01-02T00:00:00Z")
