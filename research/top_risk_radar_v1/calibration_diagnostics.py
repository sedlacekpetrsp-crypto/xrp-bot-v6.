"""Pure, synthetic-testable calibration diagnostics for future XRP radar OOS evaluation.

This module does not train a model, run an OOS evaluation, or infer any edge.
Only evaluate predictions generated strictly before their target outcome.
"""
from __future__ import annotations

from math import isfinite
from typing import Sequence


def binary_calibration_diagnostics(
    probabilities: Sequence[float],
    outcomes: Sequence[bool],
    *,
    bins: int = 10,
) -> dict:
    """Compute Brier score and reliability bins from already-validated OOS pairs.

    This function cannot verify PIT provenance: callers MUST separately prove
    prediction timestamps, label availability, fixed model, and chronological OOS.
    Empty bins are reported with count=0 and observed_rate=None.
    """
    if type(bins) is not int or bins < 2 or bins > 100:
        raise ValueError("bins must be an integer in [2, 100]")
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must have equal length")
    if not probabilities:
        return {"status": "insufficient_oos", "n": 0, "brier": None, "bins": []}
    sums = [0.0] * bins
    events = [0] * bins
    counts = [0] * bins
    brier_sum = 0.0
    for probability, outcome in zip(probabilities, outcomes):
        if type(probability) not in (int, float) or not isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("probabilities must be finite numbers in [0, 1]")
        if type(outcome) is not bool:
            raise TypeError("outcomes must be bool")
        index = min(int(probability * bins), bins - 1)
        counts[index] += 1
        sums[index] += probability
        events[index] += int(outcome)
        brier_sum += (probability - int(outcome)) ** 2
    return {
        "status": "diagnostics_only_not_validated",
        "n": len(probabilities),
        "brier": brier_sum / len(probabilities),
        "bins": [
            {
                "lower": i / bins,
                "upper": (i + 1) / bins,
                "n": counts[i],
                "mean_predicted": sums[i] / counts[i] if counts[i] else None,
                "observed_rate": events[i] / counts[i] if counts[i] else None,
            }
            for i in range(bins)
        ],
    }
