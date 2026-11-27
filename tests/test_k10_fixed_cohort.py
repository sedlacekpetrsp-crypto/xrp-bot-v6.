from datetime import datetime, timedelta, timezone
import pytest
from research.k10_fixed_cohort import CohortMember, fixed_cohort_coverage
from research.k10_label_pit_gate import ArchivedLabel

T = datetime(2020, 1, 1, tzinfo=timezone.utc)
# synthetic, syntactically valid classic addresses (not real accounts)
A, B, C = "r" + "A" * 25, "r" + "B" * 25, "r" + "C" * 25
SHA = "0" * 64


def lab(acct=A, at=None):
    return ArchivedLabel(acct, "SyntheticEx", at or T - timedelta(days=2), SHA,
                         "https://web.archive.org/web/20191230000000id_/https://example.org/")


def labels():
    return {A: lab()}


def cohort():
    return [CohortMember(A, T-timedelta(days=1), 1), CohortMember(B, T-timedelta(days=1), 2)]

def test_unknown_remains_in_denominator():
    assert fixed_cohort_coverage(cohort(), {A: 79, B: 21}, labels(), T) == (0.79, False)

def test_exact_boundary():
    assert fixed_cohort_coverage(cohort(), {A: 80, B: 20}, labels(), T) == (0.8, True)

def test_unknown_cannot_be_dropped():
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: 80}, labels(), T)

def test_posthoc_cohort_rejected():
    c = [CohortMember(A, T, 1)]
    with pytest.raises(ValueError):
        fixed_cohort_coverage(c, {A: 10}, labels(), T)

def test_unranked_extra_destination_rejected():
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: 80, B: 20, C: 1}, labels(), T)

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True])
def test_invalid_volume(value):
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: value, B: 20}, labels(), T)

def test_duplicate_rank_rejected():
    c = [CohortMember(A, T-timedelta(days=1), 1), CohortMember(B, T-timedelta(days=1), 1)]
    with pytest.raises(ValueError):
        fixed_cohort_coverage(c, {A: 80, B: 20}, labels(), T)

def test_zero_denominator_rejected():
    with pytest.raises(ValueError):
        fixed_cohort_coverage(cohort(), {A: 0, B: 0}, labels(), T)

# MINOR-1 (0384-claude): single shared as-of for the whole cohort
def test_mixed_ranked_at_rejected():
    c = [CohortMember(A, T-timedelta(days=400), 1), CohortMember(B, T-timedelta(seconds=1), 2)]
    with pytest.raises(ValueError, match="single ranking as-of"):
        fixed_cohort_coverage(c, {A: 80, B: 20}, labels(), T)

# MINOR-2: labels must be ArchivedLabel, keyed by own account, captured strictly before sample
@pytest.mark.parametrize("bad", ["captured 2025", object(), None])
def test_non_archived_label_rejected(bad):
    with pytest.raises(ValueError, match="ArchivedLabel"):
        fixed_cohort_coverage(cohort(), {A: 90, B: 10}, {A: bad}, T)

def test_label_keyed_by_other_account_rejected():
    with pytest.raises(ValueError, match="ArchivedLabel"):
        fixed_cohort_coverage(cohort(), {A: 90, B: 10}, {A: lab(B)}, T)

@pytest.mark.parametrize("at", [T, T + timedelta(days=1)])
def test_late_label_rejected(at):
    with pytest.raises(ValueError, match="strictly prior"):
        fixed_cohort_coverage(cohort(), {A: 90, B: 10}, {A: lab(A, at)}, T)

# MINOR-3: cohort addresses must be XRPL classic addresses
@pytest.mark.parametrize("addr", ["not-an-address", "rAAA", "r0" + "A" * 24, 123])
def test_invalid_cohort_address_rejected(addr):
    c = [CohortMember(addr, T-timedelta(days=1), 1)]
    with pytest.raises(ValueError, match="invalid or duplicate"):
        fixed_cohort_coverage(c, {addr: 10}, {}, T)
