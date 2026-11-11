"""Raw +30%/720h descriptive labels; no model, signals, or trading."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable

from research.top_risk_radar_v1.label_events import Label, Trade, label_touch

HORIZON = timedelta(hours=720)
GROWTH_RATIO = Decimal("1.30")


def label_decision(decision_at: datetime, trades: Iterable[Trade], as_of: datetime) -> Label:
    """Use the same reference/QA contract as downside, with a separate target.

    A touch is not profit. Negative labels require independent coverage QA;
    evaluation must retain only fully matured windows, including positives.
    """
    return label_touch(decision_at, trades, as_of, horizon=HORIZON, ratio=GROWTH_RATIO)
