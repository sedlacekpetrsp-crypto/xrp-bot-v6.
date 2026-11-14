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
READY = {**GOOD, "qa_status": "verified"}


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
    ({"acquisition_utc": "2025-01-31T00:00:00Z"}, "acquisition_before_coverage_end"),
])
def test_unready_source_fails_before_folds(change, reason):
    with pytest.raises(ValueError, match=reason):
        prepare({**READY, **change})


def test_verified_manifest_cannot_mask_missing_calendar_day():
    with pytest.raises(ValueError, match="coverage incomplete"):
        prepare(decisions=[DECISIONS[0], DECISIONS[1], DECISIONS[3]])
