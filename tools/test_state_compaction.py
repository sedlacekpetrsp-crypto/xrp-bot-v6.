"""Testy bezeztrátové kontroly kompakce STATE.md (dialog 0331 bod 5). Bez sítě."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "tools/autopilot")
from check_state_compaction import check  # noqa: E402

ARCH = "a\nb\nc\nd\ne\n"
MAN = {"source_sha256": hashlib.sha256(ARCH.encode()).hexdigest(),
       "segments": [{"lines": [1, 2], "where": "archive"}, {"lines": [3, 4], "where": "state"},
                    {"lines": [5, 5], "where": "archive"}]}
STATE = "# nový\n<!-- orig:3-4 -->\nc\nd\n<!-- /orig -->\nshrnutí\n"


def test_ok():
    r = check(STATE, ARCH, MAN)
    assert r["ok"], r["errors"]
    assert r["rebuilt_sha256"] == MAN["source_sha256"]


def test_edited_kept_segment_fails():
    r = check(STATE.replace("d\n", "D\n", 1), ARCH, MAN)
    assert not r["ok"]


def test_reordered_kept_segment_fails():
    r = check(STATE.replace("c\nd\n", "d\nc\n"), ARCH, MAN)
    assert not r["ok"]


def test_gap_in_segments_fails():
    man = json.loads(json.dumps(MAN))
    man["segments"][2]["lines"] = [6, 6]
    assert not check(STATE, ARCH, man)["ok"]


def test_tampered_archive_fails():
    assert not check(STATE, ARCH.replace("e", "E"), MAN)["ok"]


def test_missing_marker_fails():
    assert not check("# nový\nc\nd\n", ARCH, MAN)["ok"]


def test_keyword_lines_reported():
    arch = "x\nSTOP tady\nc\n"
    man = {"source_sha256": hashlib.sha256(arch.encode()).hexdigest(),
           "segments": [{"lines": [1, 2], "where": "archive"}, {"lines": [3, 3], "where": "state"}]}
    r = check("<!-- orig:3-3 -->\nc\n<!-- /orig -->\n", arch, man)
    assert r["ok"] and r["archive_only_keyword_lines"] == [{"line": 2, "keywords": ["STOP"]}]


def test_repository_compaction_is_lossless():
    if not Path("automation/archive/STATE-compaction-manifest.json").exists():
        return
    rev = subprocess.run(["git", "log", "-1", "--format=%H", "--", "automation/archive/STATE-compaction-manifest.json"],
                         capture_output=True, text=True).stdout.strip()
    args = [sys.executable, "tools/autopilot/check_state_compaction.py"] + (["--rev", rev] if rev else [])
    assert subprocess.run(args, capture_output=True).returncode == 0
