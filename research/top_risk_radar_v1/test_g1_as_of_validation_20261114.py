"""Synthetic QA for invalid G1 evaluation cutoffs; no performance test."""
from datetime import datetime, timezone, timedelta
import pytest
from research.top_risk_radar_v1.g1_preflight import validated_g1_folds

DECISIONS = [datetime(2022, 1, 1, 0, 5, tzinfo=timezone.utc)]

@pytest.mark.parametrize("bad_as_of", [
    None,
    "2026-11-14T00:00:00Z",
    0,
    datetime(2026, 11, 14),
    datetime(2026, 11, 14, tzinfo=timezone(timedelta(hours=1))),
])
def test_g1_rejects_invalid_as_of_with_controlled_error(bad_as_of):
    with pytest.raises(ValueError, match="G1 as_of must"):
        validated_g1_folds(DECISIONS, as_of=bad_as_of)

def test_g1_accepts_utc_as_of():
    folds = validated_g1_folds(DECISIONS, as_of=datetime(2026, 11, 14, tzinfo=timezone.utc))
    assert len(folds) == 5
