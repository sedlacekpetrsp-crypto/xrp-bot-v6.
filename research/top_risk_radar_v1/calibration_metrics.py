"""Canonical probability-scoring contract for both XRP PAPER radars (P1, DELIVERY-01).

This is the ONLY scoring API the future pipeline may import. The former parallel
APIs (`calibration.py`, `calibration_diagnostics.py`) were removed on 2026-11-12
because they disagreed on label type, log-loss clipping and empty-bin schema
(see research/RADAR_CALIBRATION_API_DIVERGENCE_20261111.md).

Contract (SCORING_VERSION "radar-scoring-v1"):
- outcomes: exact int 0/1 only (bool, None, floats, strings rejected) - the caller
  converts mature labels explicitly; unknown/immature labels are never coerced to 0;
- probabilities: finite real numbers in [0, 1], bool rejected;
- inputs non-empty and of equal length (exclusion counts are reported by the pipeline);
- log loss: `eps=None` (default) => false certainty gives +inf; a float eps in
  (0, 0.5) clips probabilities to [eps, 1-eps] and the eps is reported in `score()`;
- reliability bins: equal width, ALL bins returned (empty ones with count=0 and
  None means), 2 <= bins <= 100, p == 1.0 belongs to the last bin.

Pure functions only: no model fit, no OOS evaluation, no market data, no trading signal.
"""
from __future__ import annotations

import math
from typing import Sequence

SCORING_VERSION = "radar-scoring-v1"
MAX_BINS = 100


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
            raise ValueError("outcome must be an observed binary label (int 0 or 1)")
        p.append(value)
        y.append(outcome)
    return p, y


def _validated_eps(eps: float | None) -> float | None:
    if eps is None:
        return None
    if isinstance(eps, bool) or not isinstance(eps, (float, int)) or not 0.0 < float(eps) < 0.5:
        raise ValueError("eps must be None or a number in (0, 0.5)")
    return float(eps)


def brier_score(probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    """Mean squared probability error; lower is better."""
    p, y = _validated(probabilities, outcomes)
    return math.fsum((a - b) ** 2 for a, b in zip(p, y)) / len(p)


def log_loss(probabilities: Sequence[float], outcomes: Sequence[int], *, eps: float | None = None) -> float:
    """Binary cross-entropy. eps=None: exact false certainty => +inf; else clip to [eps, 1-eps]."""
    p, y = _validated(probabilities, outcomes)
    clip = _validated_eps(eps)
    terms = []
    for a, b in zip(p, y):
        if clip is not None:
            a = min(max(a, clip), 1.0 - clip)
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
) -> list[dict]:
    """Equal-width reliability bins [0,1/bins), ..., [(bins-1)/bins, 1]; all bins returned.

    Callers must filter to mature, uncensored, PIT-valid OOS labels FIRST.
    """
    p, y = _validated(probabilities, outcomes)
    if type(bins) is not int or not 2 <= bins <= MAX_BINS:
        raise ValueError(f"bins must be an integer in [2, {MAX_BINS}]")
    counts = [0] * bins
    sum_p = [0.0] * bins
    sum_y = [0] * bins
    for a, b in zip(p, y):
        index = min(int(a * bins), bins - 1)
        counts[index] += 1
        sum_p[index] += a
        sum_y[index] += b
    return [
        {"bin": i, "lower": i / bins, "upper": (i + 1) / bins, "count": counts[i],
         "mean_prediction": sum_p[i] / counts[i] if counts[i] else None,
         "event_rate": sum_y[i] / counts[i] if counts[i] else None}
        for i in range(bins)
    ]


def brier_skill_score(
    probabilities: Sequence[float], reference_probabilities: Sequence[float], outcomes: Sequence[int]
) -> float | None:
    """1 - BS(model)/BS(reference) on identical rows; None when the reference is perfect.

    Diagnostic only: a positive point estimate is not evidence of an edge without CI.
    """
    if len(probabilities) != len(reference_probabilities):
        raise ValueError("model and reference must score identical rows")
    reference = brier_score(reference_probabilities, outcomes)
    model = brier_score(probabilities, outcomes)
    if reference == 0.0:
        return None
    return 1.0 - model / reference


def score(
    probabilities: Sequence[float], outcomes: Sequence[int], *, bins: int = 10, eps: float | None = None
) -> dict:
    """Single versioned scoring record for predictions.csv consumers."""
    p, y = _validated(probabilities, outcomes)
    return {
        "scoring_version": SCORING_VERSION,
        "status": "diagnostic_only",
        "n": len(p),
        "event_rate": sum(y) / len(y),
        "brier": brier_score(p, y),
        "log_loss": log_loss(p, y, eps=eps),
        "log_loss_eps": _validated_eps(eps),
        "bins": calibration_bins(p, y, bins=bins),
    }
