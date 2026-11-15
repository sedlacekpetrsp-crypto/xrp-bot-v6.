"""Synthetic-only checks for the combined G1 metadata and calendar gate."""
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.g1_preflight import (
    complete_g1_folds, complete_g1_folds_with_manifest,
)
from research.top_risk_radar_v1.test_source_manifest import GOOD

START = datetime(2022, 1, 1, 0, 5, tzinfo=timezone.utc)
AS_OF = datetime(2026, 11, 14, tzinfo=timezone.utc)
DAY = timedelta(days=1)
DECISIONS = [START + i * DAY for i in range(4)]
READY = {**GOOD, "qa_status": "verified", "start_utc": "2022-01-01T00:00:00Z", "end_utc": "2022-01-05T00:00:00Z"}


def prepare(manifest=READY, decisions=DECISIONS):
    return complete_g1_folds_with_manifest(
        decisions, as_of=AS_OF, coverage_start=START,
        coverage_end=START + 3 * DAY, source_manifest=manifest,
    )


def test_verified_metadata_and_complete_calendar_preserve_fixed_folds():
    assert prepare() == complete_g1_folds(
        DECISIONS, as_of=AS_OF, coverage_start=START,
        coverage_end=START + 3 * DAY,
    )


@pytest.mark.parametrize("change,reason", [
    ({"qa_status": "pending"}, "source_not_verified"),
    ({"qa_status": "rejected"}, "source_not_verified"),
    ({"point_in_time_supported": False}, "pit_not_supported"),
    ({"raw_sha256": "bad"}, "invalid_sha256"),
    ({"acquisition_utc": "2022-01-04T00:00:00Z"}, "acquisition_before_coverage_end"),
])
def test_unready_source_fails_before_folds(change, reason):
    with pytest.raises(ValueError, match=reason):
        prepare({**READY, **change})


def test_verified_manifest_cannot_mask_missing_calendar_day():
    with pytest.raises(ValueError, match="coverage incomplete"):
        prepare(decisions=[DECISIONS[0], DECISIONS[1], DECISIONS[3]])


@pytest.mark.parametrize("change", [
    {"start_utc": "2022-01-02T00:00:00Z"},
    {"end_utc": "2022-01-04T00:05:00Z"},
    {"start_utc": "2025-01-01T00:00:00Z", "end_utc": "2025-02-01T00:00:00Z"},
])
def test_verified_source_must_cover_entire_decision_interval(change):
    with pytest.raises(ValueError, match="does not cover decision interval"):
        prepare({**READY, **change})


def test_source_end_after_last_decision_is_accepted():
    assert prepare({**READY, "end_utc": "2022-01-04T00:05:01Z"}) == prepare()

@pytest.mark.parametrize("bad_bound", [
    START.replace(tzinfo=None),
    "2022-01-01T00:05:00Z",
    START.replace(hour=1),
])
@pytest.mark.parametrize("bound_name", ["coverage_start", "coverage_end"])
def test_manifest_preflight_rejects_invalid_bounds_with_value_error(bad_bound, bound_name):
    bounds = {"coverage_start": START, "coverage_end": START + 3 * DAY}
    bounds[bound_name] = bad_bound
    with pytest.raises(ValueError, match="must be (UTC|a datetime|exactly 00:05)"):
        complete_g1_folds_with_manifest(
            DECISIONS, as_of=AS_OF, source_manifest=READY, **bounds,
        )


@pytest.mark.parametrize("invalid_manifest", [None, [], "verified", 42, True])
def test_non_mapping_manifest_fails_closed(invalid_manifest):
    with pytest.raises(ValueError, match="invalid_manifest_type"):
        prepare(manifest=invalid_manifest)


@pytest.mark.parametrize("bad_as_of", [
    None,
    "2026-11-14T00:00:00Z",
    AS_OF.replace(tzinfo=None),
    AS_OF.replace(tzinfo=timezone(timedelta(hours=1))),
])
def test_manifest_preflight_rejects_invalid_as_of_before_fold_creation(bad_as_of):
    """An apparently ready source must not bypass evaluation-time validation."""
    with pytest.raises(ValueError, match="G1 as_of must be"):
        complete_g1_folds_with_manifest(
            DECISIONS, as_of=bad_as_of, coverage_start=START,
            coverage_end=START + 3 * DAY, source_manifest=READY,
        )


@pytest.mark.parametrize("decisions", [
    DECISIONS[1:],  # Missing the independently declared first day.
    DECISIONS[:-1],  # Missing the independently declared last day.
])
def test_manifest_preflight_rejects_missing_edge_days(decisions):
    with pytest.raises(ValueError, match="coverage incomplete"):
        prepare(decisions=decisions)


@pytest.mark.parametrize("decisions,reason", [
    ([DECISIONS[0], DECISIONS[0], *DECISIONS[1:]], "duplicate or out of order"),
    ([DECISIONS[1], DECISIONS[0], *DECISIONS[2:]], "duplicate or out of order"),
    ([DECISIONS[0].replace(tzinfo=None), *DECISIONS[1:]], "must be UTC"),
    ([DECISIONS[0].replace(minute=6), *DECISIONS[1:]], "exactly 00:05"),
    ([START - DAY, *DECISIONS], "decision outside audited interval"),
    ([*DECISIONS, START + 4 * DAY], "decision outside audited interval"),
])
def test_manifest_preflight_rejects_invalid_decision_grid(decisions, reason):
    """Verified source metadata cannot excuse malformed or out-of-scope grid rows."""
    with pytest.raises(ValueError, match=reason):
        prepare(decisions=decisions)
