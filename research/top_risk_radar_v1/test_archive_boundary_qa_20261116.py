"""Fail-closed archive boundary checks; synthetic only, no performance evaluation."""
import hashlib
import io
import zipfile

import pytest

from research.top_risk_radar_v1.inspect_one_archive import analyze

MEMBER = "XRPUSDT-trades-2024-01-02.csv"
T0 = "1704153600000"
T1 = "1704153601000"


def make_archive(rows, extra_member=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MEMBER, "\n".join(rows) + ("\n" if rows else ""))
        if extra_member:
            z.writestr(extra_member, "irrelevant")
    data = stream.getvalue()
    return data, hashlib.sha256(data).hexdigest()


def trade(trade_id, timestamp):
    return f"{trade_id},0.60,1,0.60,{timestamp},false,true"


def test_archive_rejects_timestamp_reversal_even_with_increasing_ids():
    data, digest = make_archive([trade(10, T1), trade(11, T0)])
    with pytest.raises(ValueError, match="nonmonotonic timestamps"):
        analyze(data, digest)


def test_archive_rejects_empty_csv():
    data, digest = make_archive([])
    with pytest.raises(ValueError, match="empty archive"):
        analyze(data, digest)


def test_archive_rejects_extra_member_even_with_valid_checksum():
    data, digest = make_archive([trade(10, T0)], "README.txt")
    with pytest.raises(ValueError, match="unexpected archive members"):
        analyze(data, digest)


def test_archive_rejects_mismatched_digest_before_parsing():
    # Invalid ZIP must fail on checksum before any ZIP parsing is attempted.
    data = b"not a zip"
    with pytest.raises(ValueError, match="checksum mismatch"):
        analyze(data, "0" * 64)


def test_archive_rejects_missing_checksum():
    data, _ = make_archive([trade(10, T0)])
    with pytest.raises(ValueError, match="missing sha256"):
        analyze(data, "not-a-checksum")
