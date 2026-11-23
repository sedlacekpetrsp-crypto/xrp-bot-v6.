"""Per-fold maturity/purge counts for G1, derived ONLY from canonical folds.

Diagnostic replacement for a parallel maturity mask (ChatGPT 5a03622): counts
come from validated_g1_folds (UTC offset 0, 00:05 grid, 14 d horizon + 14 d
embargo), so they cannot diverge from what the G1 runner will actually use.
Synthetic/unit only; no I/O, no fitting, no performance.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from .g1_preflight import validated_g1_folds


def g1_fold_maturity_counts(decisions: Sequence[datetime], *, as_of: datetime) -> dict[int, dict[str, int]]:
    """Return {test_year: {train, purged_or_unmatured_train, test, excluded_unmatured_test}}.

    purged_or_unmatured_train = decisions in train years (>= 2018, < test year)
    that the canonical contract does NOT use for training (horizon+embargo purge
    before the test year, or label not mature at as_of). Immature labels are
    never counted as negatives.
    """
    decisions = list(decisions)
    folds = validated_g1_folds(decisions, as_of=as_of)
    out: dict[int, dict[str, int]] = {}
    for f in folds:
        eligible = sum(1 for d in decisions if 2018 <= d.year < f.test_year)
        out[f.test_year] = {
            "train": len(f.train_indices),
            "purged_or_unmatured_train": eligible - len(f.train_indices),
            "test": len(f.test_indices),
            "excluded_unmatured_test": len(f.excluded_unmatured),
        }
    return out
