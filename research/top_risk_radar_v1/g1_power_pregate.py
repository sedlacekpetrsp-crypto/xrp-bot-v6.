"""G1 POWER NO-GO pre-gate (manifest draft v2, Δ4). Labels + calendar only.

Runs BEFORE any model is fitted. The signature deliberately accepts no
features and no predictions: the verdict may depend only on decision dates,
frozen labels and the frozen G1 fold contract. No I/O, no fitting, no P/L.

Frozen thresholds (set 2026-11-22, run #98, before any model output exists):
- pooled OOS grouped positive episodes >= 15
- at least 3 folds each with >= 3 grouped positive episodes
Otherwise POWER_NO_GO: the single approved G1 performance run is NOT consumed.

Episode grouping uses an explicit 14-day separation (manifest v1 §3). The
legacy default of episodes.group_positive_episodes (30 d) must never be used
implicitly here.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Sequence

from .episodes import group_positive_episodes
from .g1_fold_contract import g1_calendar_folds

G1_EPISODE_SEPARATION = timedelta(days=14)
MIN_POOLED_EPISODES = 15
MIN_EVALUABLE_FOLDS = 3
MIN_EPISODES_PER_FOLD = 3
PREGATE_VERSION = "g1-power-pregate-v1"


def _validate(decisions: Sequence[datetime], labels: Sequence[Optional[bool]]) -> None:
    if len(decisions) != len(labels):
        raise ValueError("decisions/labels length mismatch")
    if not decisions:
        raise ValueError("empty decision grid")
    for lab in labels:
        # bool is a subclass of int; reject 0/1, numpy bools, strings etc.
        if lab is not None and type(lab) is not bool:
            raise ValueError("labels must be True, False or None (excluded)")


def labels_fingerprint(decisions: Sequence[datetime], labels: Sequence[Optional[bool]]) -> str:
    """SHA-256 of a canonical CSV-like serialization (decision ISO, 1/0/NA)."""
    _validate(decisions, labels)
    h = hashlib.sha256()
    for d, lab in zip(decisions, labels):
        v = "NA" if lab is None else ("1" if lab else "0")
        h.update(f"{d.isoformat()},{v}\n".encode())
    return h.hexdigest()


def _episodes(decisions, labels, indices):
    idx = [i for i in indices if labels[i] is not None]
    return group_positive_episodes(
        [decisions[i] for i in idx], [labels[i] for i in idx],
        max_separation=G1_EPISODE_SEPARATION,
    )


def g1_power_pregate(decisions: Sequence[datetime], labels: Sequence[Optional[bool]], *,
                     as_of: datetime) -> dict:
    """Return a JSON-serialisable pre-gate artefact (power_pregate.json).

    labels[i] is None when decision i was excluded upstream (missing minutes,
    no trade in first 60 s); excluded rows never form or bridge episodes.
    Per-fold counts group within the fold; the pooled count groups across all
    OOS test rows, so an episode spanning a year boundary counts once pooled.
    """
    _validate(decisions, labels)
    folds = g1_calendar_folds(decisions, as_of=as_of)
    per_fold = []
    all_test = []
    for f in folds:
        eps = _episodes(decisions, labels, f.test_indices)
        evaluated = sum(1 for i in f.test_indices if labels[i] is not None)
        per_fold.append({
            "test_year": f.test_year,
            "test_rows": len(f.test_indices),
            "evaluated_rows": evaluated,
            "excluded_label_rows": len(f.test_indices) - evaluated,
            "unmatured_rows": len(f.excluded_unmatured),
            "grouped_positive_episodes": len(eps),
            "evaluable": len(eps) >= MIN_EPISODES_PER_FOLD,
        })
        all_test.extend(f.test_indices)
    pooled = len(_episodes(decisions, labels, sorted(set(all_test))))
    n_eval_folds = sum(1 for r in per_fold if r["evaluable"])
    reasons = []
    if pooled < MIN_POOLED_EPISODES:
        reasons.append(f"pooled_episodes_{pooled}_lt_{MIN_POOLED_EPISODES}")
    if n_eval_folds < MIN_EVALUABLE_FOLDS:
        reasons.append(f"evaluable_folds_{n_eval_folds}_lt_{MIN_EVALUABLE_FOLDS}")
    return {
        "version": PREGATE_VERSION,
        "verdict": "POWER_NO_GO" if reasons else "POWER_OK",
        "reasons": reasons,
        "as_of": as_of.isoformat(),
        "thresholds": {
            "min_pooled_episodes": MIN_POOLED_EPISODES,
            "min_evaluable_folds": MIN_EVALUABLE_FOLDS,
            "min_episodes_per_fold": MIN_EPISODES_PER_FOLD,
            "episode_separation_days": G1_EPISODE_SEPARATION.days,
        },
        "pooled_grouped_positive_episodes": pooled,
        "evaluable_folds": n_eval_folds,
        "folds": per_fold,
        "labels_sha256": labels_fingerprint(decisions, labels),
        "uses_features": False,
        "uses_predictions": False,
        "note": "POWER_OK is necessary, not sufficient: B1-B4, B6 and the LOCKED manifest remain blockers.",
    }


def dumps(artefact: dict) -> str:
    return json.dumps(artefact, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
