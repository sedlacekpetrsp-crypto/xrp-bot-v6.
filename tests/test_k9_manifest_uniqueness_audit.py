import pytest

from research.k9_round_number.manifest_uniqueness_audit import validate_manifest_months

SHA = "a" * 64


def record(symbol="XRPUSDT", month="2023-01", status="OK", sha256=SHA):
    return dict(symbol=symbol, month=month, status=status, sha256=sha256)


def test_valid_distinct_months():
    assert validate_manifest_months({"months": [record(), record(month="2023-02")]})["eligible_months"] == 2


@pytest.mark.parametrize("months", [
    [record(), record()],
    [record(month="2023-13")],
    [record(symbol="xrp")],
    [record(sha256="bad")],
    [record(status="UNKNOWN")],
    [record(status="MISSING")],
    [],
    [None],
])
def test_fail_closed(months):
    with pytest.raises(ValueError):
        validate_manifest_months({"months": months})


def test_same_month_different_assets_allowed():
    assert validate_manifest_months({"months": [record(), record(symbol="BTCUSDT")]})["unique_months"] == 2
