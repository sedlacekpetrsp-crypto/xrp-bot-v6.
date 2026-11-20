"""Synthetic-only K10 byte-integrity checks; no market data or backtest."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from dataclasses import replace
import unittest

from research.k10_snapshot_bytes_gate import Snapshot, verify_snapshot


class SnapshotBytesGateTests(unittest.TestCase):
    def setUp(self):
        t = datetime(2023, 1, 1, tzinfo=timezone.utc)
        content = b"archived exchange attribution fixture"
        self.valid = Snapshot(
            "https://web.archive.org/web/20230101000000id_/https://example.org/labels.csv", t, t + timedelta(days=1),
            sha256(content).hexdigest(), content,
        )

    def test_valid_snapshot(self):
        self.assertEqual(verify_snapshot(self.valid), self.valid.expected_sha256)

    def test_modified_bytes(self):
        with self.assertRaises(ValueError):
            verify_snapshot(replace(self.valid, content=b"tampered"))

    def test_future_capture(self):
        with self.assertRaises(ValueError):
            verify_snapshot(replace(self.valid, captured_at=self.valid.decision_at + timedelta(seconds=1)))

    def test_naive_time(self):
        with self.assertRaises(ValueError):
            verify_snapshot(replace(self.valid, decision_at=datetime(2024, 1, 1)))

    def test_non_utc_offset(self):
        with self.assertRaises(ValueError):
            verify_snapshot(replace(self.valid, captured_at=datetime(2023, 1, 1, tzinfo=timezone(timedelta(hours=1)))))

    def test_bad_digest(self):
        for digest in ("", "A" * 64, "0" * 63):
            with self.subTest(digest=digest):
                with self.assertRaises(ValueError):
                    verify_snapshot(replace(self.valid, expected_sha256=digest))

    def test_bad_source(self):
        for url in ("http://archive.example.org/1", "https://user:pass@archive.example.org/1",
                    "https://archive.example.org/1#fragment", "https:///missing"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    verify_snapshot(replace(self.valid, source_url=url))

    def test_equal_decision_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "captured after decision"):
            verify_snapshot(replace(self.valid, decision_at=self.valid.captured_at))

    def test_url_timestamp_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "differs from archive URL"):
            verify_snapshot(replace(self.valid, source_url=self.valid.source_url.replace("20230101", "20240101")))

    def test_untrusted_host_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid source URL"):
            verify_snapshot(replace(self.valid, source_url=self.valid.source_url.replace("web.archive.org", "evil.example")))

    def test_non_raw_wayback_rejected(self):
        with self.assertRaisesRegex(ValueError, "raw Wayback id_"):
            verify_snapshot(replace(self.valid, source_url=self.valid.source_url.replace("id_/", "/")))

    def test_invalid_port_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid source URL"):
            verify_snapshot(replace(self.valid, source_url=self.valid.source_url.replace("web.archive.org", "web.archive.org:99999")))

    def test_empty_or_wrong_type_bytes(self):
        for payload in (b"", "text", None):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    verify_snapshot(replace(self.valid, content=payload))


if __name__ == "__main__":
    unittest.main()
