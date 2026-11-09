"""Synthetic PIT availability tests; no market data or performance backtest."""
from datetime import datetime, timedelta, timezone
import pytest
from research.top_risk_radar_v1.pit_prevalence import PITObservation, pit_historical_prevalence

CUT = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
H = timedelta(days=40)


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_late_publication_and_unknown_availability_excluded(target, horizon):
    known = PITObservation(CUT-H, CUT-timedelta(seconds=1), True, False)
    late = PITObservation(CUT-H-timedelta(days=1), CUT+timedelta(microseconds=1), False, True)
    unknown = PITObservation(CUT-H-timedelta(days=2), None, False, True)
    result = pit_historical_prevalence([known, late, unknown], CUT, horizon_days=horizon, target=target)
    assert result == {"status": "descriptive_pit_baseline", "n": 1, "rate": 1.0 if target == "growth" else 0.0}


@pytest.mark.parametrize("target,horizon", [("growth", 30), ("downside", 14)])
def test_exact_publication_boundary_inclusive(target, horizon):
    row = PITObservation(CUT-timedelta(days=horizon), CUT, True, False)
    assert pit_historical_prevalence([row], CUT, horizon_days=horizon, target=target)["n"] == 1


def test_same_instant_duplicate_across_offsets_rejected():
    from datetime import timezone as tz
    alt = CUT.astimezone(tz(timedelta(hours=2)))
    rows = [PITObservation(CUT-H, CUT-timedelta(days=1), True, False),
            PITObservation((CUT-H).astimezone(tz(timedelta(hours=2))), alt, False, True)]
    with pytest.raises(ValueError, match="duplicate"):
        pit_historical_prevalence(rows, CUT, horizon_days=14, target="downside")


def test_naive_availability_rejected_even_if_label_unknown():
    rows = [PITObservation(CUT-H, datetime(2026, 11, 8), None, None)]
    with pytest.raises(ValueError, match="timezone-aware"):
        pit_historical_prevalence(rows, CUT, horizon_days=14, target="downside")


def test_availability_before_decision_rejected():
    rows = [PITObservation(CUT-H, CUT-H-timedelta(microseconds=1), True, False)]
    with pytest.raises(ValueError, match="before"):
        pit_historical_prevalence(rows, CUT, horizon_days=30, target="growth")


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "14"])
def test_invalid_horizon_rejected(bad):
    with pytest.raises(ValueError):
        pit_historical_prevalence([], CUT, horizon_days=bad, target="growth")


def test_missing_availability_is_not_imputed():
    row = PITObservation(CUT-H, None, True, True)
    assert pit_historical_prevalence([row], CUT, horizon_days=30, target="growth") == {
        "status": "insufficient_train", "n": 0, "rate": None
    }
