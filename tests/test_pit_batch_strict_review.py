"""Review (dialog 0461) of 62a4a79/8c223ce vs Q32 and canonical assess_event (e344063). Synthetic only."""
import importlib.util
import os
from datetime import datetime, timedelta, timezone

import pytest

from research.pit_batch_strict_diagnostic import audit_batch

T = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)


def row(key="a", seen=None, published=None, **extra):
    seen = seen or T - timedelta(minutes=5)
    r = {"event_id": key, "published_at": published or seen, "first_seen_at": seen}
    r.update(extra)
    return r


# --- accepted fixes (0460 R1/R2) ---
def test_r1_same_instant_rejected():
    assert audit_batch([row(seen=T)], T)[0] == []


def test_r2_future_row_quarantined_not_fatal():
    ok, bad = audit_batch([row("a"), row("b", seen=T + timedelta(hours=1))], T)
    assert [r["event_id"] for r in ok] == ["a"] and bad[0][1] == "not_yet_available"


def test_offset_equivalent_instant_rejected():
    cet = timezone(timedelta(hours=1))
    assert audit_batch([row(seen=T.astimezone(cet))], T)[0] == []


# --- open findings ---
@pytest.mark.xfail(strict=True, reason="B1 MAJOR: row without source_id/archive_id/effective_at is eligible; "
                   "canonical assess_event (e344063) returns DATA_NO_GO missing_evidence")
def test_missing_provenance_fields_rejected():
    ok, _ = audit_batch([row()], T)
    assert ok == []


@pytest.mark.xfail(strict=True, reason="B1 MAJOR: effective_at < published_at not checked "
                   "(canonical: effective_before_publication)")
def test_effective_before_publication_rejected():
    r = row(effective_at=T - timedelta(days=1), source_id="s", archive_id="x")
    ok, _ = audit_batch([r], T)
    assert ok == []


@pytest.mark.xfail(strict=True, reason="B2 MINOR: duplicated unhashable event_id raises TypeError (set of ids) instead of per-row quarantine")
def test_duplicated_unhashable_identity_quarantined():
    r = {"event_id": ["a"], "published_at": T, "first_seen_at": T}
    ok, bad = audit_batch([r, dict(r)], T)
    assert ok == [] and [b[1] for b in bad] == ["invalid_identity"] * 2


def test_differential_vs_canonical_time_rule():
    """Time rule alone (all evidence fields present) agrees with canonical gate on a boundary grid."""
    path = os.environ.get("CANON_GATE")
    if not path:
        pytest.skip("CANON_GATE not set")
    spec = importlib.util.spec_from_file_location("canon", path)
    canon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(canon)
    mism = 0
    for d_seen in (-120, -1, 0, 1, 120):
        for d_pub in (-60, 0, 30):
            seen = T + timedelta(seconds=d_seen)
            pub = seen + timedelta(seconds=d_pub)
            ok, _ = audit_batch([row(seen=seen, published=pub)], T)
            ev = {"event_id": "a", "published_at": pub.isoformat(), "first_seen_at": seen.isoformat(),
                  "effective_at": pub.isoformat(), "source_id": "s", "archive_id": "x"}
            c = canon.assess_event(ev, T.isoformat())["status"] == "PIT_TIME_PASS_ONLY"
            mism += (bool(ok) != c)
    assert mism == 0
