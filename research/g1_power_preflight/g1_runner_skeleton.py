"""G1 runner skeleton (bloker B4) -- SYNTHETIC ONLY, no market I/O, no model fitting.

Implements only the *evaluation* half of the G1 runner from the freeze manifest
(v1 par. 6 order of verdicts, v2 Delta1/Delta4, v3 Delta6/Delta7):

    one-shot guard -> G0/pre-gate status -> input validation (fail-closed)
    -> per-fold Brier losses -> pooled BSS (ratio of sums) -> stratified paired
    CBB CI for 14 d and 28 d blocks -> verdict in the frozen order.

What it deliberately does NOT do (owners in brackets):
  * fit M0/B1/B2/B3 or internal validation (B1, ChatGPT) -- predictions and the
    ex-ante reference choice are *inputs*; the runner only checks that the
    reference was recorded before the test predictions (Delta7 audit flag);
  * load data (B3) or build the G0 manifest (B4 data part);
  * write artifacts or touch GitHub Actions (B4 workflow part, par. 9).

Nothing here may be run on real predictions before the manifest is LOCKED.
"""
from __future__ import annotations

import math
import numbers
from collections.abc import Mapping, Sequence

from research.g1_power_preflight.g1_block_bootstrap import percentile_interval
from research.g1_power_preflight.g1_stratified_cbb import _finite_fsum, stratified_paired_bss

FROZEN_BLOCKS = (14, 28)
FROZEN_REPLICATES = 2000
FROZEN_SEED = 20261112
MIN_EPISODES_PER_EVALUABLE_FOLD = 3
MIN_EVALUABLE_FOLDS = 3
MIN_TOTAL_EPISODES = 20          # v1 par. 7 LOW_N gate
GO_MIN_BSS = 0.05
NO_GO_MAX_CI_UPPER = 0.02
CAL_SLOPE_RANGE = (0.5, 2.0)
REFERENCE_NAMES = ("M0", "B1", "B2")


class InvalidRun(ValueError):
    """Any condition that v1 par. 6 step 1 maps to INVALID_RUN."""


def check_one_shot_guard(github_sha: str, locked_sha: str, confirm: str) -> None:
    """par. 9: GITHUB_SHA must equal the LOCKED manifest SHA and confirm token must match."""
    if not (isinstance(github_sha, str) and isinstance(locked_sha, str) and isinstance(confirm, str)):
        raise InvalidRun("guard inputs must be strings")
    if len(locked_sha) != 40 or any(c not in "0123456789abcdef" for c in locked_sha):
        raise InvalidRun("locked_sha must be a full lowercase 40-hex SHA")
    if github_sha != locked_sha:
        raise InvalidRun("GITHUB_SHA != locked manifest SHA")
    if confirm != f"G1-ONE-SHOT-{locked_sha}":
        raise InvalidRun("confirm token mismatch")


def _real(x, label: str) -> float:
    # m1 (review 06880e4): accept numpy scalars, reject bool and non-finite.
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise InvalidRun(f"{label}: non-real value")
    v = float(x)
    if not math.isfinite(v):
        raise InvalidRun(f"{label}: non-finite value")
    return v


def _validate_fold(fold: Mapping, max_block: int) -> dict:
    name = fold.get("name")
    if not isinstance(name, str) or not name:
        raise InvalidRun("fold name required")
    ref = fold.get("reference_name")
    if ref not in REFERENCE_NAMES:
        raise InvalidRun(f"{name}: reference must be one of {REFERENCE_NAMES}")
    if fold.get("reference_selected_before_test") is not True:
        raise InvalidRun(f"{name}: reference not recorded ex-ante (Delta7)")
    y_raw, pc_raw, pr_raw = fold.get("y"), fold.get("p_candidate"), fold.get("p_reference")
    if not (isinstance(y_raw, Sequence) and isinstance(pc_raw, Sequence) and isinstance(pr_raw, Sequence)):
        raise InvalidRun(f"{name}: y/p_candidate/p_reference must be sequences")
    n = len(y_raw)
    if n != len(pc_raw) or n != len(pr_raw):
        raise InvalidRun(f"{name}: length mismatch")
    if n < 2 * max_block:                       # Delta6 point 4
        raise InvalidRun(f"{name}: {n} paired days < 2*{max_block}")
    y = []
    for v in y_raw:
        if isinstance(v, bool) or not isinstance(v, numbers.Integral) or int(v) not in (0, 1):
            raise InvalidRun(f"{name}: labels must be 0/1 integers")
        y.append(int(v))
    pc = [_real(v, f"{name} p_candidate") for v in pc_raw]
    pr = [_real(v, f"{name} p_reference") for v in pr_raw]
    if any(not 0.0 <= p <= 1.0 for p in pc):
        raise InvalidRun(f"{name}: candidate probability outside [0,1]")
    # Delta6 point 5 / m2: every reference day loss must be > 0 ex-ante.
    if any(not 0.0 < p < 1.0 for p in pr):
        raise InvalidRun(f"{name}: reference probability must be in (0,1)")
    ep = fold.get("grouped_positive_episodes")
    if isinstance(ep, bool) or not isinstance(ep, numbers.Integral) or ep < 0:
        raise InvalidRun(f"{name}: grouped_positive_episodes must be int >= 0")
    if ep > 0 and sum(y) == 0:
        raise InvalidRun(f"{name}: episodes > 0 but no positive label")
    loss_c = [(p - t) ** 2 for p, t in zip(pc, y)]
    loss_r = [(p - t) ** 2 for p, t in zip(pr, y)]
    return {"name": name, "reference_name": ref, "n": n, "episodes": int(ep),
            "y": y, "p_candidate": pc, "loss_c": loss_c, "loss_r": loss_r}


def _bss(loss_c: Sequence[float], loss_r: Sequence[float], label: str) -> float:
    den = _finite_fsum(loss_r, f"{label} reference loss sum")
    if den <= 0:
        raise InvalidRun(f"{label}: Brier(ref) = 0")
    out = 1.0 - _finite_fsum(loss_c, f"{label} candidate loss sum") / den
    if not math.isfinite(out):
        raise InvalidRun(f"{label}: non-finite BSS")
    return out


def calibration_slope(y: Sequence[int], p: Sequence[float], *, eps: float = 1e-6,
                      max_iter: int = 100) -> float:
    """Slope b of logit P(y=1) = a + b*logit(p), Newton-Raphson, stdlib only."""
    xs = [math.log(min(max(q, eps), 1 - eps) / (1 - min(max(q, eps), 1 - eps))) for q in p]
    if len(set(y)) < 2 or max(xs) - min(xs) <= 0:
        raise InvalidRun("calibration slope undefined (one class or constant predictions)")
    a = b = 0.0
    for _ in range(max_iter):
        ga = gb = haa = hab = hbb = 0.0
        for x, t in zip(xs, y):
            z = a + b * x
            m = 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))
            w = m * (1 - m)
            ga += t - m
            gb += (t - m) * x
            haa += w
            hab += w * x
            hbb += w * x * x
        det = haa * hbb - hab * hab
        if det <= 1e-300:
            raise InvalidRun("calibration slope: singular Hessian (separation)")
        da = (hbb * ga - hab * gb) / det
        db = (haa * gb - hab * ga) / det
        a += da
        b += db
        if not (math.isfinite(a) and math.isfinite(b)) or abs(b) > 1e6:
            raise InvalidRun("calibration slope diverged")
        if abs(da) < 1e-10 and abs(db) < 1e-10:
            return b
    raise InvalidRun("calibration slope did not converge")


def evaluate_g1(folds: Sequence[Mapping], *, g0_ok: bool, pregate_status: str,
                blocks: tuple[int, ...] = FROZEN_BLOCKS,
                replicates: int = FROZEN_REPLICATES, seed: int = FROZEN_SEED) -> dict:
    """Return a result dict with ``verdict`` in the frozen v1 par. 6 order.

    ``pregate_status`` is the output of the Delta4 POWER pre-gate (PR #77); anything
    other than ``"PASS"`` stops the runner before any metric is computed.
    """
    frozen = (tuple(blocks) == FROZEN_BLOCKS and replicates == FROZEN_REPLICATES
              and seed == FROZEN_SEED)
    base = {"status": "SYNTHETIC_ONLY", "frozen_config": frozen, "flags": [],
            "label": "EXPLORATORY_SCREEN"}
    # Step 1: INVALID_RUN
    try:
        if g0_ok is not True:
            raise InvalidRun("G0 data manifest not OK / SHA mismatch")
        if not folds:
            raise InvalidRun("no folds")
        clean = [_validate_fold(f, max(blocks)) for f in folds]
        if len({f["name"] for f in clean}) != len(clean):
            raise InvalidRun("duplicate fold names")
    except InvalidRun as exc:
        return {**base, "verdict": "INVALID_RUN", "reason": str(exc)}
    # Step 2a: pre-gate / LOW_N (no metric computed yet)
    if pregate_status != "PASS":
        return {**base, "verdict": "POWER_NO_GO", "reason": f"pre-gate {pregate_status!r}"}
    total_ep = sum(f["episodes"] for f in clean)
    if total_ep < MIN_TOTAL_EPISODES:
        return {**base, "verdict": "INCONCLUSIVE_LOW_N", "reason": f"{total_ep} grouped episodes"}
    evaluable = [f for f in clean if f["episodes"] >= MIN_EPISODES_PER_EVALUABLE_FOLD]
    if len(evaluable) < MIN_EVALUABLE_FOLDS:
        return {**base, "verdict": "INCONCLUSIVE_LOW_FOLDS",
                "reason": f"{len(evaluable)} evaluable folds"}
    # Metrics (all folds pooled, Delta6 point 3: ratio of sums, weight = days).
    try:
        per_fold = []
        for f in clean:
            per_fold.append({"name": f["name"], "n": f["n"], "episodes": f["episodes"],
                             "reference": f["reference_name"],
                             "evaluable": f["episodes"] >= MIN_EPISODES_PER_EVALUABLE_FOLD,
                             "bss": _bss(f["loss_c"], f["loss_r"], f["name"])})
        pooled = _bss([x for f in clean for x in f["loss_c"]],
                      [x for f in clean for x in f["loss_r"]], "pooled")
        cis = {}
        for blk in blocks:
            try:
                reps = stratified_paired_bss([(f["loss_c"], f["loss_r"]) for f in clean],
                                             block_days=blk, replicates=replicates, seed=seed)
            except ValueError as exc:
                raise InvalidRun(f"CI not computable (block {blk}): {exc}") from exc
            if len(reps) != replicates:
                raise InvalidRun("CI not computable: missing replicates")
            cis[blk] = percentile_interval(reps, alpha=0.05)
    except (InvalidRun, ValueError) as exc:
        return {**base, "verdict": "INVALID_RUN", "reason": str(exc)}
    # Calibration slope is a GO-only condition: undefined slope blocks GO but must not
    # turn a NO-GO into INVALID_RUN (NO-GO has precedence, v1 par. 6 step 3).
    try:
        slope = calibration_slope([t for f in clean for t in f["y"]],
                                  [p for f in clean for p in f["p_candidate"]])
    except InvalidRun:
        slope = None
        base["flags"].append("CAL_SLOPE_UNDEFINED")
    result = {**base, "pooled_bss": pooled, "ci95": {str(k): v for k, v in cis.items()},
              "calibration_slope": slope, "per_fold": per_fold,
              "evaluable_folds": len(evaluable), "total_episodes": total_ep,
              "comparisons_per_fold": 3 + 4}
    # Step 3: NO-GO (precedence over GO)
    if not frozen:
        result["flags"].append("NON_FROZEN_CONFIG")
    if pooled <= 0 and any(lo > 0 for lo, _ in cis.values()):
        result["flags"].append("CI_POINT_CONFLICT")
    if pooled <= 0 or any(hi < NO_GO_MAX_CI_UPPER for _, hi in cis.values()):
        return {**result, "verdict": "NO-GO"}
    # Step 4: GO
    k = len(evaluable)
    positive_folds = sum(1 for pf in per_fold if pf["evaluable"] and pf["bss"] > 0)
    need = math.ceil(2 * k / 3)
    result["positive_evaluable_folds"] = positive_folds
    result["required_positive_folds"] = need
    if (pooled >= GO_MIN_BSS and all(lo > 0 for lo, _ in cis.values())
            and positive_folds >= need
            and slope is not None and CAL_SLOPE_RANGE[0] <= slope <= CAL_SLOPE_RANGE[1]):
        return {**result, "verdict": "GO"}
    # Step 5
    return {**result, "verdict": "INCONCLUSIVE"}
