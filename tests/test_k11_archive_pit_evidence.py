"""Synthetic-only tests for K11 archived-title evidence (no downloads)."""
from datetime import datetime, timedelta, timezone
import pytest
from research.k11_archive_pit_evidence import classify_archive_evidence

T = datetime(2025, 5, 1, 12, tzinfo=timezone.utc)


def test_no_archive_is_unverified():
    assert classify_archive_evidence(T, [])[0] == "unverified"


def test_on_time_positive_is_ok():
    assert classify_archive_evidence(T, [(T, True)])[0] == "ok"


def test_24h_boundary_inclusive():
    assert classify_archive_evidence(T, [(T + timedelta(hours=24), True)])[0] == "ok"


def test_late_capture_is_unverified():
    assert classify_archive_evidence(T, [(T + timedelta(hours=24, seconds=1), True)])[0] == "unverified"


def test_early_positive_contradicts_even_with_later_positive():
    status, proof = classify_archive_evidence(T, [
        (T - timedelta(hours=25), True), (T + timedelta(hours=1), True)])
    assert status == "contradicted"
    assert proof["earliest_contradiction_utc"] is not None


def test_early_boundary_not_contradiction():
    assert classify_archive_evidence(T, [
        (T - timedelta(hours=24), True), (T + timedelta(hours=1), True)])[0] == "ok"


def test_before_release_not_corroboration():
    assert classify_archive_evidence(T, [(T - timedelta(minutes=1), True)])[0] == "unverified"


def test_duplicate_conflicting_capture_fails_closed():
    with pytest.raises(ValueError):
        classify_archive_evidence(T, [(T, True), (T, False)])


def test_naive_time_rejected():
    with pytest.raises(ValueError):
        classify_archive_evidence(T.replace(tzinfo=None), [])


def test_non_boolean_title_flag_rejected():
    with pytest.raises(ValueError):
        classify_archive_evidence(T, [(T, 1)])


def test_negative_observation_is_not_positive():
    assert classify_archive_evidence(T, [(T, False)])[0] == "unverified"


def test_duplicate_identical_capture_deduplicated():
    _, evidence = classify_archive_evidence(T, [(T, True), (T, True)])
    assert evidence["observations"] == 1
