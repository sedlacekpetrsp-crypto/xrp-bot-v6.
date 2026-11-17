from datetime import datetime, timedelta, timezone
import pytest
from research.k10_fixed_cohort import CohortMember, fixed_cohort_coverage

T = datetime(2020, 1, 1, tzinfo=timezone.utc)
A, B, C = "rAAA", "rBBB", "rCCC"
def cohort():
    return [CohortMember(A, T-timedelta(days=1), 1), CohortMember(B, T-timedelta(days=1), 2)]

def test_unknown_remains_in_denominator():
    assert fixed_cohort_coverage(cohort(), {A: 79, B: 21}, {A: object()}, T) == (0.79, False)

def test_exact_boundary():
    assert fixed_cohort_coverage(cohort(), {A: 80, B: 20}, {A: object()}, T) == (0.8, True)

def test_unknown_cannot_be_dropped():
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: 80}, {A: object()}, T)

def test_posthoc_cohort_rejected():
    c = [CohortMember(A, T, 1)]
    with pytest.raises(ValueError):
        fixed_cohort_coverage(c, {A: 10}, {A: object()}, T)

def test_unranked_extra_destination_rejected():
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: 80, B: 20, C: 1}, {A: object()}, T)

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True])
def test_invalid_volume(value):
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: value, B: 20}, {A: object()}, T)

def test_duplicate_rank_rejected():
    c = [CohortMember(A, T-timedelta(days=1), 1), CohortMember(B, T-timedelta(days=1), 1)]
    with pytest.raises(ValueError):
        fixed_cohort_coverage(c, {A: 80, B: 20}, {A: object()}, T)

def test_zero_denominator_rejected():
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: 0, B: 0}, {A: object()}, T)
