"""Paired circular moving-block bootstrap for G1 Brier Skill Score (PAPER only).

This is a diagnostic primitive, not a performance run. Both loss streams share
identical sampled indices. No tuning, no market data and no production hooks.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence


def paired_block_bss(model_losses: Sequence[float], reference_losses: Sequence[float],
                     *, block_days: int, replicates: int, seed: int) -> list[float]:
    """Return BSS replicates; reject undefined denominators instead of inventing scores.

    Circular blocks preserve sample length even when n < block_days; callers must
    separately document whether circular wrapping is appropriate for their folds.
    """
    if not isinstance(block_days, int) or isinstance(block_days, bool) or block_days < 1:
        raise ValueError("block_days must be a positive integer")
    if not isinstance(replicates, int) or isinstance(replicates, bool) or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if len(model_losses) != len(reference_losses) or not model_losses:
        raise ValueError("paired nonempty equal-length losses required")
    for losses in (model_losses, reference_losses):
        if any(not isinstance(v, (int, float)) or isinstance(v, bool)
               or not math.isfinite(v) or v < 0 for v in losses):
            raise ValueError("losses must be finite nonnegative numbers")
    n = len(model_losses)
    if sum(reference_losses) <= 0:
        raise ValueError("reference Brier loss is zero; BSS undefined")
    rng = random.Random(seed)
    output = []
    for _ in range(replicates):
        indices = []
        while len(indices) < n:
            start = rng.randrange(n)
            indices.extend((start + j) % n for j in range(block_days))
        indices = indices[:n]
        denom = math.fsum(reference_losses[i] for i in indices)
        if denom <= 0:
            raise ValueError("resampled reference loss zero; BSS undefined")
        numer = math.fsum(model_losses[i] for i in indices)
        output.append(1.0 - numer / denom)
    return output


def percentile_interval(samples: Sequence[float], *, alpha: float = 0.05) -> tuple[float, float]:
    """Linear-interpolation empirical quantiles, deterministic and stdlib-only."""
    if not samples or not 0 < alpha < 1 or any(not math.isfinite(x) for x in samples):
        raise ValueError("valid samples and 0 < alpha < 1 required")
    ordered = sorted(samples)
    def quantile(q: float) -> float:
        pos = (len(ordered) - 1) * q
        lo = math.floor(pos)
        hi = math.ceil(pos)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)
    return quantile(alpha / 2), quantile(1 - alpha / 2)
