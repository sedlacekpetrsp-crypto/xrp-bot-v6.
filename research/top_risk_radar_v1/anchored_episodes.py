"""Alternative episode accounting that prevents transitive chaining.

A descriptive sensitivity check only. Positive daily labels overlap and
episode counts must not be interpreted as independent forecast successes.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from typing import Sequence

def anchored_episodes(dates: Sequence[datetime], *, horizon_days: int) -> list[dict]:
    if horizon_days<=0: raise ValueError("horizon must be positive")
    if any(a>=b for a,b in zip(dates,dates[1:])):
        raise ValueError("dates must be strictly increasing")
    out=[]
    horizon=timedelta(days=horizon_days)
    for dt in dates:
        if out and dt-out[-1]["first_decision"]<=horizon:
            out[-1]["last_decision"]=dt
            out[-1]["positive_decisions"]+=1
        else:
            out.append({"first_decision":dt,"last_decision":dt,
                        "positive_decisions":1})
    return out
