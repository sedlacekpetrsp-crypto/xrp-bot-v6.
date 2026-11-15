"""Synthetic G0 archive integrity regressions; no downloads or performance runs."""
import hashlib
import io
import zipfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from research.top_risk_radar_v1.inspect_one_archive import analyze


def archive(rows):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("XRPUSDT-trades-2024-01-02.csv", "\n".join(rows) + "\n")
    blob = payload.getvalue()
    return blob, hashlib.sha256(blob).hexdigest()


def row(trade_id, price="0.60", ts="1704153600000"):
    return f"{trade_id},{price},1,0.60,{ts},false,true"


def test_valid_archive_keeps_integrity_unverified():
    blob, digest = archive([row(10), row(11, ts="1704153601000")])
    result = analyze(blob, digest)
    assert result["row_count"] == 2
    assert result["checksum_verified"] is True
    assert result["coverage_status"] == "not_yet_independently_verified"


@pytest.mark.parametrize("rows,expected", [
    ([row(10), row(10, ts="1704153601000")], "trade ID"),
    ([row(11), row(10, ts="1704153601000")], "trade ID"),
    ([row(10, "NaN")], "price"),
    ([row(10, "Infinity")], "price"),
    ([row(10, "-1")], "price"),
    ([row(10, ts="1704067200000"), row(11)], "out-of-day"),
    ([row(10), row(11, ts="1704240000000")], "out-of-day"),
])
def test_archive_fail_closed_on_trade_integrity(rows, expected):
    blob, digest = archive(rows)
    with pytest.raises(ValueError, match=expected):
        analyze(blob, digest)
