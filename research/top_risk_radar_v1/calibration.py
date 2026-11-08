"""Pure probability calibration diagnostics; no model fitting or backtest.

Use only on an explicitly authorized, chronologically held-out prediction set.
Rows are (probability, observed_event), with mature Boolean labels only.
"""
from __future__ import annotations
import math
from typing import Sequence

def calibration_metrics(rows: Sequence[tuple[float, bool]], *, bins: int = 10) -> dict:
    """Compute Brier/log loss and fixed-width reliability bins without fitting.

    Reject unknown/immature labels rather than treating them as negatives.
    Empty bins are represented with n=0 and observed_rate=None.
    """
    if type(bins) is not int or bins < 2 or bins > 100:
        raise ValueError("bins must be an integer between 2 and 100")
    counts = [0] * bins
    predicted = [0.0] * bins
    observed = [0] * bins
    brier = logloss = 0.0
    n = 0
    for p, y in rows:
        if type(y) is not bool:
            raise TypeError("labels must be mature Boolean events")
        if isinstance(p, bool) or not isinstance(p, (float, int)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("probabilities must be finite and within [0, 1]")
        p = float(p)
        idx = min(int(p * bins), bins - 1)
        counts[idx] += 1
        predicted[idx] += p
        observed[idx] += int(y)
        brier += (p - int(y)) ** 2
        # Clipping is only for finite log-loss, not for Brier or bins.
        safe = min(max(p, 1e-15), 1 - 1e-15)
        logloss -= math.log(safe) if y else math.log1p(-safe)
        n += 1
    return {
        "status": "diagnostic_only" if n else "insufficient_data",
        "n": n,
        "event_rate": sum(observed) / n if n else None,
        "brier": brier / n if n else None,
        "log_loss": logloss / n if n else None,
        "bins": [
            {"lower": i / bins, "upper": (i + 1) / bins, "n": counts[i],
             "mean_prediction": predicted[i] / counts[i] if counts[i] else None,
             "observed_rate": observed[i] / counts[i] if counts[i] else None}
            for i in range(bins)
        ],
    }
