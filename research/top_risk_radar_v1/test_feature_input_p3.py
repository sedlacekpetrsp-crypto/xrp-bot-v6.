"""Integration regression for review 0301: open-time leakage and provenance."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import pytest

from research.top_risk_radar_v1.feature_input import DailyInput, adapt_daily, build_feature_bundle

D = datetime(2026, 11, 12, 0, 5, tzinfo=timezone.utc)


def rows(symbol):
    start = D.replace(minute=0) - timedelta(days=31)
    return [DailyInput(symbol, start + timedelta(days=i),
                       start + timedelta(days=i+1, minutes=1),
                       start + timedelta(days=i+1, minutes=2),
                       100.0 + i, "synthetic", "fixture-v1", "accepted", "a" * 64)
            for i in range(31)]


def test_real_features_and_serialization_keep_provenance_and_order():
    x, b = rows("XRPUSDT"), rows("BTCUSDT")
    bundle = build_feature_bundle(x, b, D)
    assert bundle == build_feature_bundle(x[::-1], b[::-1], D)
    decoded = json.loads(bundle[0])
    assert len(decoded["sources"]) == 62
    assert decoded["features"]["relative_log_return_30d"] == 0
    assert decoded["features"]["max_event_time_utc"] == D.replace(minute=0).isoformat()
    assert decoded["sources"][0]["provider"] == "synthetic"
    changed = [replace(x[0], payload_sha256="b" * 64)] + x[1:]
    assert build_feature_bundle(changed, b, D)[1] != bundle[1]


def test_open_today_rejected_even_with_fabricated_early_publication():
    row = replace(rows("XRPUSDT")[-1], open_time=D.replace(minute=0))
    with pytest.raises(ValueError, match="not_yet_available"):
        adapt_daily(row, D)


@pytest.mark.parametrize("changes,reason", [
    ({"published_at": None}, "invalid_source_or_timezone"),
    ({"received_at": D}, "not_yet_available"),
    ({"provider": ""}, "missing_provenance"),
    ({"quality_flag": "unknown"}, "quality_excluded"),
    ({"payload_sha256": "unknown"}, "invalid_payload_hash"),
    ({"close": True}, "invalid_close"),
    ({"close": float("inf")}, "invalid_close"),
    ({"received_at": D.replace(minute=0)}, "invalid_source_chronology"),
])
def test_bad_source_evidence_fails_closed(changes, reason):
    with pytest.raises(ValueError, match=reason):
        adapt_daily(replace(rows("XRPUSDT")[-1], **changes), D)


def test_gap_is_not_filled_by_adapter():
    with pytest.raises(ValueError, match="insufficient_lookback"):
        build_feature_bundle(rows("XRPUSDT")[:-1], rows("BTCUSDT"), D)


def test_int_and_float_close_produce_identical_bundle_hash():
    x, b = rows("XRPUSDT"), rows("BTCUSDT")
    integer_close = [replace(x[0], close=int(x[0].close)), *x[1:]]
    assert build_feature_bundle(x, b, D) == build_feature_bundle(integer_close, b, D)


def test_mixed_provider_within_symbol_series_rejected():
    x, b = rows("XRPUSDT"), rows("BTCUSDT")
    mixed = [*x[:-1], replace(x[-1], provider="other_exchange")]
    with pytest.raises(ValueError, match="mixed_provider_in_symbol_series"):
        build_feature_bundle(mixed, b, D)
