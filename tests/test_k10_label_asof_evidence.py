from datetime import datetime, timedelta, timezone
import pytest
from research.k10_label_asof_evidence import LabelEvidence, asof_labels

T = datetime(2020, 1, 1, tzinfo=timezone.utc)
def e(address="rA", public=None, captured=None, label="exchange", source="archived-snapshot"):
    return LabelEvidence(address, label, public or T-timedelta(days=2),
                         captured or T-timedelta(days=1), source)

def test_valid_archived_label():
    assert asof_labels(["rA", "rB"], [e()], T) == {"rA": "exchange"}

def test_future_capture_not_retroactive():
    assert asof_labels(["rA"], [e(captured=T+timedelta(days=1))], T) == {}

def test_future_publication_not_retroactive():
    assert asof_labels(["rA"], [e(public=T+timedelta(days=1), captured=T+timedelta(days=2))], T) == {}

def test_publication_after_capture_rejected():
    with pytest.raises(ValueError):
        asof_labels(["rA"], [e(public=T, captured=T-timedelta(days=1))], T)

def test_conflicting_duplicate_evidence_rejected():
    with pytest.raises(ValueError):
        asof_labels(["rA"], [e(), e(label="unknown")], T)

def test_unrelated_address_rejected():
    with pytest.raises(ValueError):
        asof_labels(["rA"], [e(address="rB")], T)

def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        asof_labels(["rA"], [e(public=datetime(2019, 1, 1))], T)

def test_missing_source_rejected():
    with pytest.raises(ValueError):
        asof_labels(["rA"], [e(source="")], T)

def test_duplicate_cohort_rejected():
    with pytest.raises(ValueError):
        asof_labels(["rA", "rA"], [e()], T)
