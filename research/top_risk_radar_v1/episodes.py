"""Collapse overlapping positive decision dates into event episodes.

Descriptive research only. NOT an estimate of predictive performance.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from typing import Sequence

def group_positive_episodes(decisions: Sequence[datetime], positives: Sequence[bool], *,
                            max_separation: timedelta=timedelta(days=30)) -> list[dict]:
    if len(decisions)!=len(positives): raise ValueError("length mismatch")
    if max_separation<timedelta(0): raise ValueError("negative separation")
    if any(a>=b for a,b in zip(decisions,decisions[1:])):
        raise ValueError("decision timestamps must be strictly increasing")
    groups=[]
    for dt,hit in zip(decisions,positives):
        if not hit: continue
        if groups and dt-groups[-1]["last_decision"]<=max_separation:
            groups[-1]["last_decision"]=dt
            groups[-1]["positive_decisions"]+=1
        else:
            groups.append({"first_decision":dt,"last_decision":dt,"positive_decisions":1})
    return groups
