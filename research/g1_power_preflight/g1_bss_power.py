"""G1 ex-ante power for the BSS decision rule of the freeze draft (synthetic only, no market data).

Purpose: before the single owner-approved G1 run is spent, estimate how often the draft decision rule
(G1_FREEZE_MANIFEST_DRAFT_20261112 §6) returns GO / NO-GO / INCONCLUSIVE for a radar of known true skill,
given the census structure (1 705 mature OOS decisions, 21 clustered episodes).

Model of the world (deliberately OPTIMISTIC for the radar):
- y_t = 1 on L consecutive days per episode, episodes non-overlapping (gap >= L + 14 d).
- score z_t = s * y_t + e_t, e_t AR(1) with phi = 0.9 (persistent features such as volatility), unit variance.
- forecast f_t = sigmoid(a + b z_t) with (a, b) fitted on a large independent synthetic train sample
  (oracle calibration; reality is worse). Reference = train prevalence (M0); the real reference is the best of
  M0/B1/B2, which can only make GO harder.
Decision rule (draft §6, calibration-slope condition omitted because forecasts are oracle-calibrated):
  GO      : BSS >= 0.05 and lower 95% CI > 0 for both 14 d and 28 d moving-block bootstrap
            and BSS > 0 in >= 2/3 of evaluatable folds (fold evaluatable if >= 3 episodes start in it);
  NO-GO   : BSS <= 0 or upper 95% CI < 0.02 for any block length;
  else INCONCLUSIVE; fewer than 3 evaluatable folds => INCONCLUSIVE.
Stdlib + numpy, deterministic (seed 20261122). N (multiple testing) +0: not a hypothesis test of any strategy.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

SEED = 20261122
N_DAYS = 1705
N_FOLDS = 5
BLOCKS = (14, 28)


def place_episodes(rng, n_days, n_eps, L, gap=14):
    span = L + gap
    free = n_days - n_eps * span
    if free < 0:
        raise ValueError("episodes do not fit")
    # stars-and-bars: uniform non-overlapping placement
    cuts = np.sort(rng.integers(0, free + 1, size=n_eps))
    starts = cuts + np.arange(n_eps) * span
    y = np.zeros(n_days, dtype=np.int8)
    for s in starts:
        y[s:s + L] = 1
    return y, starts


def ar1(rng, n, phi=0.9):
    e = rng.standard_normal(n) * math.sqrt(1 - phi * phi)
    out = np.empty(n)
    out[0] = rng.standard_normal()
    for i in range(1, n):
        out[i] = phi * out[i - 1] + e[i]
    return out


def fit_logit(z, y, iters=50):
    X = np.column_stack([np.ones_like(z), z])
    w = np.zeros(2)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (y - p)
        H = (X * (p * (1 - p))[:, None]).T @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, g)
        w += step
        if np.abs(step).max() < 1e-10:
            break
    return w


def block_bootstrap_bss(bm, br, block, B, rng):
    n = len(bm)
    nb = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    return 1 - bm[idx].sum(1) / br[idx].sum(1)


def simulate(s, n_eps, L, sims, B, rng):
    # oracle calibration on a large independent train sample
    ytr = np.concatenate([place_episodes(rng, N_DAYS, n_eps, L)[0] for _ in range(40)]).astype(float)
    ztr = s * ytr + np.concatenate([ar1(rng, N_DAYS) for _ in range(40)])
    a, b = fit_logit(ztr, ytr)
    prev = ytr.mean()
    fold_edges = np.linspace(0, N_DAYS, N_FOLDS + 1).astype(int)
    counts = {"GO": 0, "NO-GO": 0, "INCONCLUSIVE": 0}
    sum_bm = sum_br = 0.0
    bss_list = []
    for _ in range(sims):
        y, starts = place_episodes(rng, N_DAYS, n_eps, L)
        z = s * y + ar1(rng, N_DAYS)
        f = 1 / (1 + np.exp(-(a + b * z)))
        bm = (f - y) ** 2
        br = (prev - y) ** 2
        sum_bm += bm.sum(); sum_br += br.sum()
        bss = 1 - bm.sum() / br.sum()
        bss_list.append(bss)
        ci = {k: np.percentile(block_bootstrap_bss(bm, br, k, B, rng), [2.5, 97.5]) for k in BLOCKS}
        ev, pos = 0, 0
        for i in range(N_FOLDS):
            lo, hi = fold_edges[i], fold_edges[i + 1]
            if ((starts >= lo) & (starts < hi)).sum() >= 3:
                ev += 1
                if 1 - bm[lo:hi].sum() / br[lo:hi].sum() > 0:
                    pos += 1
        if ev < 3:
            v = "INCONCLUSIVE"
        elif bss <= 0 or any(ci[k][1] < 0.02 for k in BLOCKS):
            v = "NO-GO"
        elif bss >= 0.05 and all(ci[k][0] > 0 for k in BLOCKS) and pos >= math.ceil(2 * ev / 3):
            v = "GO"
        else:
            v = "INCONCLUSIVE"
        counts[v] += 1
    return {
        "true_bss_pooled": round(1 - sum_bm / sum_br, 4),
        "bss_median": round(float(np.median(bss_list)), 4),
        **{f"P_{k}": round(c / sims, 3) for k, c in counts.items()},
    }


def main(sims=300, B=1000):
    rng = np.random.default_rng(SEED)
    out = {"meta": {"seed": SEED, "n_days": N_DAYS, "sims": sims, "bootstrap": B, "blocks": BLOCKS,
                    "phi": 0.9, "reference": "train prevalence (M0), optimistic"}, "grid": []}
    for n_eps, L in ((21, 8), (21, 14), (14, 8)):
        for s in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
            r = simulate(s, n_eps, L, sims, B, rng)
            out["grid"].append({"n_eps": n_eps, "L": L, "s": s, **r})
    return out


if __name__ == "__main__":
    sims = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    print(json.dumps(main(sims=sims), indent=1))
