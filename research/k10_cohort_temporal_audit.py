"""K10 independent pre-sample cohort temporal audit (PAPER, no performance)."""
from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass(frozen=True)
class CohortWindow:
    sample_start: datetime
    ranking_start: datetime
    ranking_end: datetime
    first_observed_at: datetime
    ledger_closed_at: datetime

def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError("UTC-aware datetime required")
    return value.astimezone(timezone.utc)

def validate_cohort_window(w: CohortWindow) -> bool:
    """Fail closed when ranking inputs or ledger finality cross the sample boundary.

    The source's *first observation* is mandatory: an old ledger timestamp
    retrieved after the sample began is not sufficient PIT evidence.
    """
    start, left, right, seen, closed = map(_utc, (
        w.sample_start, w.ranking_start, w.ranking_end,
        w.first_observed_at, w.ledger_closed_at))
    if not left < right < start:
        raise ValueError("ranking window must end strictly before sample")
    if not right <= closed <= seen < start:
        raise ValueError("ledger close and first observation must precede sample")
    return True
