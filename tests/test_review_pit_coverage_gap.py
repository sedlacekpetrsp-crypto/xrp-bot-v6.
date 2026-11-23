"""Claude review (dialog 0464) of cd6ee40/c4168ac. Synthetic only; strict xfail = known defect."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("pit_cov_review", Path(__file__).resolve().parents[1] / "research" / "pit_coverage_gap_diagnostic.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
t = datetime(2026, 1, 1, tzinfo=timezone.utc)
h = timedelta(hours=1)


@pytest.mark.xfail(strict=True, reason="M1: single terminal decision_time hides per-row lateness (backfill right before end => COMPLETE)")
def test_backfilled_feed_is_not_complete_for_rolling_decisions():
    obs = [(t, t + 2 * h), (t + h, t + 2 * h), (t + 2 * h, t + 2 * h)]
    r = mod.audit_coverage([t, t + h, t + 2 * h], obs, t + 3 * h)
    assert r["late"] >= 2  # rows t, t+h were not available at their own next decision


@pytest.mark.xfail(strict=True, reason="m2: grid point == decision is accepted but can never be usable under strict <")
def test_grid_point_at_decision_rejected_or_usable():
    with pytest.raises(ValueError):
        mod.audit_coverage([t, t + h], [(t, t), (t + h, t + h)], t + h)


def test_strict_boundary_consistent_with_q16():
    assert mod.audit_coverage([t], [(t, t + h - timedelta(microseconds=1))], t + h)["usable"] == 1
    assert mod.audit_coverage([t], [(t, t + h)], t + h)["late"] == 1
