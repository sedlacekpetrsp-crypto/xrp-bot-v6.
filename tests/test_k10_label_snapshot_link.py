import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from research.k10_label_pit_gate import ArchivedLabel
from research.k10_label_snapshot_link import validate_linked_labels
from research.k10_snapshot_bytes_gate import Snapshot

START = datetime(2021, 1, 1, tzinfo=timezone.utc)
CAP = datetime(2020, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
A1 = "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh"
A2 = "rLHzPsX6oXkzU2qL12kHCH8G8cnZv1rBJh"
URL = "https://web.archive.org/web/20201201120000id_/https://example.org/exchanges"
BODY = f"<tr><td>Synthetic Exchange</td><td>{A1}</td><td>{A2}</td></tr>".encode()
DIGEST = sha256(BODY).hexdigest()


def snap(**kw):
    v = dict(source_url=URL, captured_at=CAP, decision_at=START, expected_sha256=DIGEST, content=BODY)
    v.update(kw)
    return Snapshot(**v)


def label(account=A1, **kw):
    v = dict(account=account, exchange="Synthetic Exchange", captured_at=CAP, content_sha256=DIGEST, source_url=URL)
    v.update(kw)
    return ArchivedLabel(**v)


class LabelSnapshotLinkTests(unittest.TestCase):
    def test_valid_two_labels_one_snapshot(self):
        out = validate_linked_labels([label(A1), label(A2)], [snap()], START)
        self.assertEqual(set(out), {A1, A2})

    def assertRejects(self, labels, snaps, reason, start=START):
        with self.assertRaisesRegex(ValueError, reason):
            validate_linked_labels(labels, snaps, start)

    def test_missing_snapshot(self):
        self.assertRejects([label()], [], "without archived snapshot")

    def test_unused_snapshot(self):
        other = URL.replace("exchanges", "other")
        self.assertRejects([label()], [snap(), snap(source_url=other)], "not referenced")

    def test_duplicate_snapshot(self):
        self.assertRejects([label()], [snap(), snap()], "duplicate snapshot")

    def test_capture_time_mismatch(self):
        self.assertRejects([label(captured_at=CAP - timedelta(seconds=1))], [snap()], "capture time differs")

    def test_digest_mismatch(self):
        self.assertRejects([label(content_sha256="0" * 64)], [snap()], "digest differs")

    def test_account_not_in_bytes(self):
        absent = "rPVMhWBsfF9iMXYj3aAzJVkPDTFNSyWdKy"
        self.assertRejects([label(absent)], [snap()], "not present in archived bytes")

    def test_tampered_bytes(self):
        self.assertRejects([label()], [snap(content=BODY + b" ")], "byte-integrity")

    def test_decision_time_must_be_sample_start(self):
        self.assertRejects([label()], [snap(decision_at=START + timedelta(days=1))], "decision time")

    def test_label_after_sample_rejected_by_base_gate(self):
        late = datetime(2021, 1, 2, tzinfo=timezone.utc)
        self.assertRejects([label(captured_at=late)], [snap()], "strictly prior", start=START)

    def test_capture_equal_to_sample_start_rejected(self):
        url = "https://web.archive.org/web/20210101000000id_/https://example.org/exchanges"
        self.assertRejects([label(captured_at=START, source_url=url)],
                           [snap(source_url=url, captured_at=START)], "strictly prior")

    def test_non_snapshot_object(self):
        self.assertRejects([label()], [object()], "invalid snapshot")


if __name__ == "__main__":
    unittest.main()
