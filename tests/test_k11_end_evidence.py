from datetime import datetime, timedelta, timezone
import pytest
from research.k11_end_evidence import coverage_with_proven_end, validated_end_minute
UTC = timezone.utc
T = datetime(2026, 1, 1, tzinfo=UTC)
M = int(T.timestamp()) // 60

def event(**kw):
    e = dict(symbol="ABCUSDT", status="TRADING_TERMINATED",
             event_time=T + timedelta(minutes=10),
             observed_at=T + timedelta(minutes=11), source_sha256="a" * 64)
    e.update(kw)
    return e

def test_midday_gap_not_proof():
    x = coverage_with_proven_end(set(range(M, M+10)), M, M+100, "ABCUSDT", [], T+timedelta(days=1))
    assert x["coverage"] == .1 and not x["truncated"]

def test_verified_end():
    x = coverage_with_proven_end(set(range(M, M+10)), M, M+100, "ABCUSDT", [event()], T+timedelta(days=1))
    assert x["coverage"] == 1 and x["truncated"]

def test_wrong_symbol():
    assert validated_end_minute("ABCUSDT", M+9, [event(symbol="XYZUSDT")], T+timedelta(days=1)) is None

def test_future_observation():
    assert validated_end_minute("ABCUSDT", M+9, [event()], T) is None

def test_wrong_status():
    assert validated_end_minute("ABCUSDT", M+9, [event(status="SUSPENDED")], T+timedelta(days=1)) is None

def test_missing_digest():
    assert validated_end_minute("ABCUSDT", M+9, [event(source_sha256="")], T+timedelta(days=1)) is None

def test_nonmatching_end():
    assert validated_end_minute("ABCUSDT", M+8, [event()], T+timedelta(days=1)) is None

def test_naive_asof():
    with pytest.raises(ValueError):
        validated_end_minute("ABCUSDT", M+9, [], datetime(2026,1,1))
