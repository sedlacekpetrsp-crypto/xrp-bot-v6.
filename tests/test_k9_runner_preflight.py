"""Regression tests for K9 runner preflight; synthetic fixtures only, no performance runs."""
import hashlib
import json

import pandas as pd
import pytest

from research.k9_round_number import phase_b_run


def test_dev_skips_final_month_without_fetch_or_read(tmp_path):
    seen = []
    def fetch(symbol, year, month, dest):
        seen.append((year, month))
        return tmp_path / "fake.zip", None
    def reader(path):
        return pd.DataFrame({"open": [100.0], "close": [100.0]},
                            index=pd.DatetimeIndex(["2023-12-01T00:00:00Z"]))
    payload = b"synthetic fixture"
    (tmp_path / "fake.zip").write_bytes(payload)
    manifest = {"months": [
        {"status": "OK", "month": "2023-12", "symbol": "BTCUSDT",
         "sha256": hashlib.sha256(payload).hexdigest()},
        {"status": "OK", "month": "2024-01", "symbol": "BTCUSDT",
         "sha256": "not-fetched"},
    ]}
    frames = phase_b_run.load_frames(manifest, tmp_path, fetch=fetch, reader=reader,
                                     before=pd.Timestamp("2024-01-01", tz="UTC"))
    assert seen == [(2023, 12)]
    assert list(frames) == ["BTCUSDT"]
    assert len(frames["BTCUSDT"]) == 1


def test_dev_with_only_final_month_never_calls_fetch(tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("final-period archive was accessed")
    manifest = {"months": [{"status": "OK", "month": "2024-02", "symbol": "XRPUSDT",
                             "sha256": "synthetic"}]}
    assert phase_b_run.load_frames(manifest, tmp_path, fetch=forbidden, reader=forbidden,
                                   before=pd.Timestamp("2024-01-01", tz="UTC")) == {}
