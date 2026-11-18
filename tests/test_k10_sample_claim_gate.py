import pytest
from research.k10_sample_claim_gate import audit_ledger_sample, assert_cohort_evidence


def test_sparse_probe_not_cohort_evidence():
    a = audit_ledger_sample(100, 200, [100, 150, 200], [200, 100, 150])
    assert not a.coverage_claim_allowed
    with pytest.raises(ValueError, match="sparse"):
        assert_cohort_evidence(a)


def test_complete_window_can_be_census():
    a = audit_ledger_sample(4, 6, [4, 5, 6], [6, 4, 5])
    assert a.full_census
    assert_cohort_evidence(a)


@pytest.mark.parametrize("requested,observed", [
    ([1, 1], [1]), ([1, 2], [1]), ([1], [1, 2]),
    ([0], [0]), ([1], [2]), ([], []),
])
def test_fail_closed(requested, observed):
    with pytest.raises(ValueError):
        audit_ledger_sample(1, 1, requested, observed)


def test_bool_index_rejected():
    with pytest.raises(ValueError):
        audit_ledger_sample(1, 2, [True], [True])
