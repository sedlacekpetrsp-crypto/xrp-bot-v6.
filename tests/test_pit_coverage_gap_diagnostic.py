"""Synthetic-only tests: no market data, performance evaluation or external access."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("pit_coverage", Path(__file__).resolve().parents[1] / "research" / "pit_coverage_gap_diagnostic.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
t = datetime(2026, 1, 1, tzinfo=timezone.utc)
h = timedelta(hours=1)


def test_complete():
    assert mod.audit_coverage([t, t+h], [(t,t), (t+h,t+h)], t+2*h)["status"] == "COMPLETE"


def test_missing_and_late():
    r = mod.audit_coverage([t,t+h,t+2*h], [(t,t), (t+h,t+3*h)], t+3*h)
    assert (r["usable"],r["missing"],r["late"],r["coverage"]) == (1,1,1,1/3)


def test_exact_decision_is_late():
    assert mod.audit_coverage([t], [(t,t+h)], t+h)["late"] == 1


def test_empty_grid():
    assert mod.audit_coverage([], [], t)["status"] == "EMPTY_GRID"


@pytest.mark.parametrize("grid,obs,decision", [
    ([t,t], [], t+h),
    ([t+h,t], [], t+2*h),
    ([t+h], [], t),
    ([t], [(t,t),(t,t+h)], t+2*h),
    ([t], [(t+h,t+h)], t+2*h),
    ([t], [(t,t-h)], t+h),
    ([t.replace(tzinfo=None)], [], t+h),
    ([t], [(t,t.replace(tzinfo=None))], t+h),
])
def test_fail_closed(grid,obs,decision):
    with pytest.raises(ValueError):
        mod.audit_coverage(grid,obs,decision)
