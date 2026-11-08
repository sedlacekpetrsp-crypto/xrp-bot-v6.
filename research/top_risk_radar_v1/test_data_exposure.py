"""Synthetic invariants for exposure ledger; not an OOS or performance run."""
from datetime import datetime, timezone, timedelta
import pytest
from research.top_risk_radar_v1.data_exposure import Exposure, validate_exposures, untouched_holdout

UTC = timezone.utc
def t(day):
    return datetime(2026, 1, day, tzinfo=UTC)
def e(a, b, level="none", evidence="frozen audit log"):
    return Exposure(t(a), t(b), level, evidence)

def test_fully_covered_none_is_eligible():
    assert untouched_holdout([e(1, 3), e(3, 7)], t(2), t(6))

def test_prevalence_viewed_is_not_untouched():
    assert not untouched_holdout([e(1, 4, "prevalence-viewed")], t(2), t(3))

def test_tuned_is_not_untouched():
    assert not untouched_holdout([e(1, 4, "tuned")], t(2), t(3))

def test_unknown_gap_fails_closed():
    assert not untouched_holdout([e(1, 3), e(4, 7)], t(2), t(6))

def test_empty_ledger_fails_closed():
    assert not untouched_holdout([], t(1), t(2))

@pytest.mark.parametrize("rows", [
    [e(1, 3), e(2, 4)],
    [e(3, 4), e(1, 2)],
    [e(2, 2)],
    [e(1, 2, "unknown")],
    [e(1, 2, evidence="")],
])
def test_malformed_ledger_rejected(rows):
    with pytest.raises(ValueError):
        validate_exposures(rows)

def test_non_utc_rejected():
    with pytest.raises(ValueError):
        untouched_holdout([e(1, 3)], t(1).replace(tzinfo=None), t(2))

def test_non_positive_request_rejected():
    with pytest.raises(ValueError):
        untouched_holdout([e(1, 3)], t(2), t(2))
