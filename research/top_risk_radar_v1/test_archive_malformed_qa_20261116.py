"""Additional fail-closed synthetic CSV integrity regressions (no backtest)."""
import pytest

from research.top_risk_radar_v1.test_archive_boundary_qa_20261116 import (
    T0, T1, make_archive,
)
from research.top_risk_radar_v1.inspect_one_archive import analyze


@pytest.mark.parametrize("row,reason", [
    (f"10,NaN,1,0.60,{T0},false,true", "invalid trade price"),
    (f"10,-0.60,1,0.60,{T0},false,true", "invalid trade price"),
    (f"10,0.60,Infinity,0.60,{T0},false,true", "invalid trade quantity"),
    (f"10,0.60,0,0.60,{T0},false,true", "invalid trade quantity"),
    (f"10,0.60,1,0.60,{T0},maybe,true", "invalid trade boolean"),
    (f"10,0.60,1,0.60,{T0},false,1", "invalid trade boolean"),
    (f"not-an-id,0.60,1,0.60,{T0},false,true", "invalid trade ID"),
    (f"10,0.60,1,0.60,{T0},false", "unexpected CSV columns"),
])
def test_rejects_malformed_numeric_boolean_and_schema(row, reason):
    payload, sha = make_archive([row])
    with pytest.raises(ValueError, match=reason):
        analyze(payload, sha)


def test_rejects_decreasing_trade_ids_with_increasing_timestamps():
    payload, sha = make_archive([
        f"11,0.60,1,0.60,{T0},false,true",
        f"10,0.60,1,0.60,{T1},false,true",
    ])
    with pytest.raises(ValueError, match="duplicate or nonmonotonic trade ID"):
        analyze(payload, sha)


def test_rejects_checksum_mismatch_on_well_formed_zip():
    payload, sha = make_archive([f"10,0.60,1,0.60,{T0},false,true"])
    tampered = payload + b"x"
    with pytest.raises(ValueError, match="checksum mismatch"):
        analyze(tampered, sha)
