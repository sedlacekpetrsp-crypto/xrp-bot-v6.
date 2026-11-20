"""Synthetic fail-closed regressions; no network, price data, or backtests."""
import json
import unittest
from research.k11_step0_collector import collect, enumerate_cms, CMS_LIST, CDX, ARCHIVE_PREFIXES


class K11MalformedInputTests(unittest.TestCase):
    def test_cms_invalid_json(self):
        articles, error = enumerate_cms(lambda _: (200, b"{"))
        self.assertIsNone(articles)
        self.assertIn("CMS invalid page 1", error)

    def test_cms_missing_data_is_not_empty_catalog(self):
        articles, error = enumerate_cms(lambda _: (200, b'{}'))
        self.assertIsNone(articles)
        self.assertIn("missing CMS data", error)

    def test_cms_invalid_collection_type(self):
        articles, error = enumerate_cms(lambda _: (200, b'{"data":{"articles":"not-a-list"}}'))
        self.assertIsNone(articles)
        self.assertIn("invalid CMS collection", error)

    def test_cdx_http_failure_is_no_go(self):
        def fetch(url):
            if "cms/article/list" in url:
                return 200, b'{"data":{"articles":[]}}'
            return 503, b""
        rows, manifest = collect(fetch)
        self.assertEqual(rows, [])
        self.assertEqual(manifest["verdict"], "DATA_NO_GO")
        self.assertIn("CDX unavailable", manifest["enumeration_error"])

    def test_cdx_malformed_json_is_no_go(self):
        def fetch(url):
            if "cms/article/list" in url:
                return 200, b'{"data":{"articles":[]}}'
            return 200, b"not-json"
        rows, manifest = collect(fetch)
        self.assertEqual(rows, [])
        self.assertEqual(manifest["verdict"], "DATA_NO_GO")
        self.assertIn("CDX malformed", manifest["enumeration_error"])

    def test_cdx_empty_200_is_zero_captures_not_no_go(self):  # review Claude: prázdný prefix = 0 snímků
        def fetch(url):
            if url.startswith("https://www.binance.com/bapi"):
                return 200, b'{"data":{"articles":[]}}'
            return 200, b""
        rows, manifest = collect(fetch)
        self.assertNotIn("enumeration_error", manifest)
        self.assertEqual(manifest["archive_captures"], 0)


if __name__ == "__main__":
    unittest.main()
