"""Deterministic calibration diagnostics shared by both XRP PAPER radars.

Pure functions only. These are evaluation primitives, NOT an OOS evaluation,
model fit, threshold optimization, market-data download or trading signal.
"""
from __future__ import annotations

import math
from typing import Sequence


def _validated(probabilities: Sequence[float], outcomes: Sequence[int]) -> tuple[list[float], list[int]]:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("nonempty probabilities and outcomes must have equal length")
    p: list[float] = []
    y: list[int] = []
    for probability, outcome in zip(probabilities, outcomes):
        if isinstance(probability, bool) or not isinstance(probability, (float, int)):
            raise TypeError("probability must be numeric, not bool")
        value = float(probability)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("probability must be finite and in [0, 1]")
        if type(outcome) is not int or outcome not in (0, 1):
            raise ValueError("outcome must be an observed binary label (0 or 1)")
        p.append(value)
        y.append(outcome)
    return p, y


def brier_score(probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    """Mean squared probability error; lower is better."""
    p, y = _validated(probabilities, outcomes)
    return math.fsum((a - b) ** 2 for a, b in zip(p, y)) / len(p)


def log_loss(probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    """Binary cross-entropy; exact false certainty has infinite loss."""
    p, y = _validated(probabilities, outcomes)
    terms = []
    for a, b in zip(p, y):
        if b:
            if a == 0.0:
                return math.inf
            terms.append(-math.log(a))
        else:
            if a == 1.0:
                return math.inf
            terms.append(-math.log1p(-a))
    return math.fsum(terms) / len(p)


def calibration_bins(
    probabilities: Sequence[float], outcomes: Sequence[int], bins: int = 10
) -> list[dict[str, float | int]]:
    """Equal-width reliability bins with deterministic boundaries.

    [0,1/bins), ..., [(bins-1)/bins,1]; empty bins omitted.
    Callers must filter to mature, uncensored, PIT-valid OOS labels FIRST.
    """
    p, y = _validated(probabilities, outcomes)
    if type(bins) is not int or bins < 2:
        raise ValueError("bins must be an integer >= 2")
    counts = [0] * bins
    sum_p = [0.0] * bins
    sum_y = [0] * bins
    for a, b in zip(p, y):
        index = min(int(a * bins), bins - 1)
        counts[index] += 1
        sum_p[index] += a
        sum_y[index] += b
    return [
        {"bin": i, "count": counts[i], "mean_prediction": sum_p[i] / counts[i],
         "event_rate": sum_y[i] / counts[i]}
        for i in range(bins) if counts[i]
    ]
