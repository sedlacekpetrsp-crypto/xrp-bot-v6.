"""Synthetic regression tests for the research coordinator evidence gate."""
import unittest

from automation.task_evidence import idempotency_key, validate

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


def task(state="DONE"):
    return {
        "task_id": "67", "state": state, "owner": "claude",
        "branch": "claude/manifest-67", "input_sha": SHA_A,
        "protocol_sha": SHA_B, "output_sha": SHA_C,
        "artifact_paths": ["reports/manifest.json"],
        "test_command": "python -m unittest",
        "test_exit_code": 0, "reviewer": "chatgpt",
        "review_note": "reviewed evidence", "blockers": [],
    }


class EvidenceGateTests(unittest.TestCase):
    def test_complete_evidence(self):
        self.assertEqual(validate(task()), [])

    def test_missing_commit_fails(self):
        x = task()
        del x["output_sha"]
        self.assertTrue(validate(x))

    def test_missing_test_evidence_fails(self):
        x = task()
        del x["test_command"]
        self.assertTrue(validate(x))

    def test_failed_test_fails(self):
        x = task()
        x["test_exit_code"] = 1
        self.assertTrue(validate(x))

    def test_self_review_fails(self):
        x = task()
        x["reviewer"] = x["owner"]
        self.assertTrue(validate(x))

    def test_blocked_done_fails(self):
        x = task()
        x["blockers"] = ["missing historical candles"]
        self.assertTrue(validate(x))

    def test_claimed_reproduction_needs_evidence(self):
        x = task()
        x["reproduced"] = True
        self.assertTrue(validate(x))

    def test_idempotency_same_inputs(self):
        self.assertEqual(idempotency_key(task()), idempotency_key(task()))

    def test_idempotency_diff_protocol(self):
        x = task()
        x["protocol_sha"] = SHA_C
        self.assertNotEqual(idempotency_key(task()), idempotency_key(x))

    def test_no_absolute_paths(self):
        x = task()
        x["artifact_paths"] = ["/tmp/report"]
        self.assertTrue(validate(x))


if __name__ == "__main__":
    unittest.main()
