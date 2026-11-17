"""Fail-closed PIT eligibility for radar training labels (diagnostic only)."""
from datetime import datetime, timedelta, timezone

class LabelEligibilityError(ValueError):
    pass

def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise LabelEligibilityError(f"{field} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise LabelEligibilityError(f"{field} must use UTC offset")
    return value.astimezone(timezone.utc)

def eligible_training_label(*, feature_at: datetime, cutoff_at: datetime,
                            horizon_days: int, label_available_at: datetime,
                            data_available_at: datetime) -> bool:
    """True only if forward label has matured and was known by training cutoff.

    Input feature data must have been available at its feature timestamp.
    Missing timestamps and impossible provenance fail closed.
    """
    feature = _utc(feature_at, "feature_at")
    cutoff = _utc(cutoff_at, "cutoff_at")
    label = _utc(label_available_at, "label_available_at")
    data = _utc(data_available_at, "data_available_at")
    if type(horizon_days) is not int or horizon_days not in (14, 30):
        raise LabelEligibilityError("horizon_days must be 14 or 30")
    if data < feature:
        raise LabelEligibilityError("data_available_at precedes feature_at")
    if label < feature + timedelta(days=horizon_days):
        raise LabelEligibilityError("label_available_at precedes label horizon")
    return (feature < cutoff and data <= feature
            and feature + timedelta(days=horizon_days) <= cutoff
            and label <= cutoff)
