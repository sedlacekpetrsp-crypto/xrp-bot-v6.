"""Synthetic serialization contract tests; no market data or performance runs."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

import pytest

from research.top_risk_radar_v1.features import DailyClose, build_daily_features
from research.top_risk_radar_v1.feature_serialization import canonical_feature_record


def _features():
    decision = datetime(2026, 11, 12, 0, 5, tzinfo=timezone.utc)
    start = decision.replace(hour=0, minute=0) - timedelta(days=30)
    def candles(symbol, growth):
        return [DailyClose(symbol, start + timedelta(days=i),
                           start + timedelta(days=i, minutes=1),
                           start + timedelta(days=i, minutes=2),
                           100.0 * math.exp(i * growth)) for i in range(31)]
    return build_daily_features(candles("XRPUSDT", 0.01), candles("BTCUSDT", 0.004), decision)


def test_canonical_hash_independent_of_dict_insertion_order():
    original = _features()
    payload, digest = canonical_feature_record(original)
    reversed_record = dict(reversed(list(original.items())))
    assert canonical_feature_record(reversed_record) == (payload, digest)
    assert hashlib.sha256(payload).hexdigest() == digest
    assert json.loads(payload) == original


def test_canonical_hash_changes_with_feature_value():
    original = _features()
    modified = dict(original, xrp_log_return_1d=original["xrp_log_return_1d"] + 0.001)
    assert canonical_feature_record(original)[1] != canonical_feature_record(modified)[1]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "0.3", None])
def test_nonfinite_or_nonnumeric_feature_rejected(bad):
    f = _features()
    f["xrp_log_return_1d"] = bad
    with pytest.raises(ValueError, match="invalid_numeric_feature"):
        canonical_feature_record(f)


def test_missing_provenance_timestamp_and_schema_rejected():
    f = _features()
    del f["max_available_at_utc"]
    with pytest.raises(ValueError, match="missing_pit_timestamp"):
        canonical_feature_record(f)
    f = _features()
    f["schema_version"] = "future-incompatible-schema"
    with pytest.raises(ValueError, match="invalid_feature_schema"):
        canonical_feature_record(f)
