"""Synthetic regression tests for the research coordinator evidence gate."""
import unittest

import subprocess
import tempfile

from automation.task_evidence import idempotency_key, validate, verify_in_repo

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


class ClaudeReviewFindings(unittest.TestCase):
    """Claude review 2026-11-07: cases the first version accepted or crashed on."""

    def test_non_string_state_fails_closed_without_crash(self):
        x = task(); x["state"] = ["DONE"]
        self.assertIn("invalid state", validate(x))

    def test_reviewer_same_as_owner_ignoring_case_and_spaces(self):
        for r in ("Claude", " claude ", "CLAUDE"):
            x = task(); x["reviewer"] = r
            self.assertIn("DONE requires different reviewer", validate(x))

    def test_reproduced_must_be_boolean(self):
        x = task(); x["reproduced"] = "yes"
        self.assertIn("reproduced must be true or false", validate(x))

    def test_idempotency_key_unambiguous_with_colon(self):
        a = task(); a["task_id"] = "a:b"
        b = task(); b["task_id"] = "a"
        self.assertNotEqual(idempotency_key(a), idempotency_key(b))

    def test_verify_in_repo_rejects_fake_sha_and_missing_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: subprocess.run(["git", "-C", d, *a], check=True, capture_output=True, text=True).stdout.strip()
            g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
            open(f"{d}/m.json", "w").write("{}"); g("add", "m.json"); g("commit", "-qm", "x")
            sha = g("rev-parse", "HEAD")
            ok = task(); ok.update(input_sha=sha, protocol_sha=sha, output_sha=sha, artifact_paths=["m.json"])
            self.assertEqual(verify_in_repo(ok, d), [])
            fake = dict(ok, output_sha="f" * 40)
            self.assertTrue(any("not found" in e for e in verify_in_repo(fake, d)))
            missing = dict(ok, artifact_paths=["neni.json"])
            self.assertTrue(any("missing" in e for e in verify_in_repo(missing, d)))
