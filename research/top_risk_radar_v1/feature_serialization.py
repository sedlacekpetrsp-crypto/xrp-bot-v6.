"""Deterministic PIT feature record serialization for PAPER radar P3 QA.

This is a pure serialization utility. It does not fetch market data, predict,
calibrate, or validate that upstream publication timestamps are authentic.
"""
from __future__ import annotations

import hashlib
import json
import math

from .features import FEATURE_SCHEMA_VERSION

_TIME_KEYS = ("decision_time_utc", "max_event_time_utc", "max_available_at_utc")


def canonical_feature_record(features: dict) -> tuple[bytes, str]:
    """Return canonical UTF-8 JSON bytes and SHA-256; reject malformed/nonfinite data.

    Key order is irrelevant, numeric values must be finite Python int/float
    (excluding bool), and the three PIT time fields must be present.
    """
    if not isinstance(features, dict) or features.get("schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("invalid_feature_schema")
    for key in _TIME_KEYS:
        if not isinstance(features.get(key), str) or not features[key]:
            raise ValueError("missing_pit_timestamp")
    numeric_keys = [k for k in features if k not in (*_TIME_KEYS, "schema_version")]
    if not numeric_keys:
        raise ValueError("missing_numeric_features")
    for key in numeric_keys:
        value = features[key]
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError("invalid_numeric_feature")
    payload = json.dumps(features, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return payload, hashlib.sha256(payload).hexdigest()
