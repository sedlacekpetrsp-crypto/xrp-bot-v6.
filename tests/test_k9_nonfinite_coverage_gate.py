"""Synthetic-only regression tests: non-finite coverage must never pass K9 gates.

No market data, network, backtest or performance run.
"""
import numpy as np
import pandas as pd
import pytest

from research.k9_round_number import phase_b


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_dev_selection_rejects_nonfinite_missing_fraction(bad):
    t = pd.DataFrame({
        "kind": ["round"], "gross": [0.01], "net_x1": [0.0086]
    })
    selection = phase_b.dev_selection({15: t, 60: t.copy()}, {15: bad, 60: 0.0})
    assert selection["final_open"] is False
    assert selection["h_star"] is None
    assert selection["verdict"].startswith("INCONCLUSIVE")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_final_gate_rejects_nonfinite_missing_fraction(monkeypatch, bad):
    monkeypatch.setattr(phase_b, "boot", lambda *a, **k: {
        "point": 1.0, "lo": 0.5, "hi": 1.5, "invalid_frac": 0.0
    })
    monkeypatch.setattr(phase_b, "dsr", lambda *a, **k: {"dsr": 1.0})
    monkeypatch.setattr(phase_b, "stability", lambda *a, **k: {"ok": True})
    t = pd.DataFrame({
        "time": [pd.Timestamp("2025-01-01", tz="UTC")],
        "net_x2": [0.01], "net_x3": [0.01]
    })
    result = phase_b.evaluate_final(
        t, t, t, pd.Series([0.01, 0.02, 0.03]), 0.99, bad, reps=2
    )
    assert result["verdict"].startswith("INCONCLUSIVE")
