from datetime import datetime, timedelta, timezone
import pytest

from research.k10_label_pit_gate import ArchivedLabel, validate_labels, volume_coverage

T = datetime(2020, 1, 1, tzinfo=timezone.utc)
A = "r" + "a" * 25
B = "r" + "b" * 25


def label(account=A, when=None, digest=None):
    return ArchivedLabel(account, "Binance", when or T - timedelta(days=1),
                         digest or "a" * 64, "https://web.archive.org/web/20191231/example")


def test_prior_archive_accepted():
    assert A in validate_labels([label()], T)


@pytest.mark.parametrize("when", [T, T + timedelta(seconds=1)])
def test_at_or_after_sample_rejected(when):
    with pytest.raises(ValueError):
        validate_labels([label(when=when)], T)


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        validate_labels([label(when=datetime(2019, 12, 31))], T)


def test_nonzero_offset_rejected():
    with pytest.raises(ValueError):
        validate_labels([label(when=datetime(2019, 12, 31, tzinfo=timezone(timedelta(hours=1))))], T)


def test_duplicate_account_rejected():
    with pytest.raises(ValueError):
        validate_labels([label(), label()], T)


def test_bad_digest_rejected():
    with pytest.raises(ValueError):
        validate_labels([label(digest="INVALID")], T)


def test_empty_labels_rejected():
    with pytest.raises(ValueError):
        validate_labels([], T)


def test_coverage_boundary():
    labels = validate_labels([label()], T)
    ratio, passed = volume_coverage([(A, 80), (B, 20)], labels)
    assert ratio == 0.8 and passed


def test_insufficient_coverage():
    labels = validate_labels([label()], T)
    assert volume_coverage([(A, 79), (B, 21)], labels)[1] is False


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 0, True])
def test_invalid_amount_fail_closed(bad):
    with pytest.raises(ValueError):
        volume_coverage([(A, bad)], {A: label()})


def test_no_payments_fail_closed():
    with pytest.raises(ValueError):
        volume_coverage([], {A: label()})
