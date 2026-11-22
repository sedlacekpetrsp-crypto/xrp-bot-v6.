"""Fold-stratified paired circular block bootstrap for G1 diagnostics.

Synthetic diagnostics only. Fold boundaries are never bridged. No market I/O.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence


def stratified_paired_bss(folds: Sequence[tuple[Sequence[float], Sequence[float]]],
                          *, block_days: int, replicates: int, seed: int) -> list[float]:
    """Sample each fold independently; aggregate paired loss sums before BSS.

    Fail closed if a fold is shorter than two full blocks, or any bootstrap
    denominator is zero. Fold membership and reference selection are ex-ante.
    """
    if type(block_days) is not int or block_days < 1:
        raise ValueError("positive integer block_days required")
    if type(replicates) is not int or replicates < 1 or type(seed) is not int:
        raise ValueError("valid replicates and integer seed required")
    if not folds:
        raise ValueError("at least one fold required")
    clean = []
    for model, ref in folds:
        if len(model) != len(ref) or len(model) < 2 * block_days:
            raise ValueError("each fold requires paired length >= 2*block_days")
        for values in (model, ref):
            if any(type(x) not in (float, int) or not math.isfinite(x) or x < 0
                   for x in values):
                raise ValueError("finite nonnegative losses required")
        if math.fsum(ref) <= 0:
            raise ValueError("reference loss must be positive in every fold")
        clean.append((tuple(model), tuple(ref)))
    rng = random.Random(seed)
    results = []
    for _ in range(replicates):
        numerator, denominator = [], []
        for model, ref in clean:
            n = len(model)
            indices = []
            while len(indices) < n:
                start = rng.randrange(n)
                indices.extend((start + k) % n for k in range(block_days))
            indices = indices[:n]
            numerator.extend(model[i] for i in indices)
            denominator.extend(ref[i] for i in indices)
        d = math.fsum(denominator)
        if d <= 0:
            raise ValueError("bootstrap reference denominator zero")
        results.append(1 - math.fsum(numerator) / d)
    return results
