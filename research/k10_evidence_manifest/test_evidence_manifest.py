import unittest
from evidence_manifest import manifest

R = {"address":"rExample","publisher":"A","source_url":"https://example.org/a",
     "observed_at":"2020-01-01T00:00:00Z","sha256":"a"*64}

class Tests(unittest.TestCase):
    def test_order(self):
        b = dict(R, publisher="B")
        self.assertEqual(manifest([R,b],"2021-01-01T00:00:00Z")["sha256"],manifest([b,R],"2021-01-01T00:00:00Z")["sha256"])
    def test_future(self):
        with self.assertRaises(ValueError): manifest([R],"2019-01-01T00:00:00Z")
    def test_duplicate(self):
        with self.assertRaises(ValueError): manifest([R,R],"2021-01-01T00:00:00Z")
    def test_naive(self):
        with self.assertRaises(ValueError): manifest([dict(R,observed_at="2020-01-01T00:00:00")],"2021-01-01T00:00:00Z")
    def test_digest(self):
        with self.assertRaises(ValueError): manifest([dict(R,sha256="bad")],"2021-01-01T00:00:00Z")
    def test_missing(self):
        with self.assertRaises(ValueError): manifest([dict(R,source_url="")],"2021-01-01T00:00:00Z")
    def test_empty(self):
        with self.assertRaises(ValueError): manifest([],"2021-01-01T00:00:00Z")
    def test_no_data_go(self):
        self.assertEqual(manifest([R],"2021-01-01T00:00:00Z")["status"],"INTEGRITY_ONLY_NOT_DATA_GO")

if __name__ == "__main__": unittest.main()
