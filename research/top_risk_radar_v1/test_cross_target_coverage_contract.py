"""Cross-target coverage regression: explicit horizon is mandatory for correct interpretation.

These tests are deterministic, synthetic and do not measure predictive performance.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from research.early_growth_radar_v1.label_events import label_decision as growth_label
from research.top_risk_radar_v1.coverage_qa import audit_coverage
from research.top_risk_radar_v1.label_events import Trade, label_decision as risk_label

T = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _stream(days: int):
    # Dense synthetic ID-contiguous feed; five-minute max gap exactly.
    count = days * 24 * 12
    return [Trade(T + timedelta(minutes=5 * i), Decimal("1"), i)
            for i in range(count + 1)]


def test_growth_14day_feed_must_fail_720hour_coverage():
    rows = _stream(14)
    as_of = T + timedelta(days=30)
    label = growth_label(T, rows, as_of)
    assert label.status == "negative_requires_coverage_qa"
    assert label.deadline_at - label.decision_at == timedelta(hours=720)
    report = audit_coverage(label.decision_at, rows, as_of,
                            horizon=label.deadline_at - label.decision_at)
    assert not report.acceptable
    assert not report.window_end_covered


def test_risk_14day_feed_uses_336hour_target_not_growth():
    rows = _stream(14)
    as_of = T + timedelta(days=14)
    label = risk_label(T, rows, as_of)
    assert label.deadline_at - label.decision_at == timedelta(hours=336)
    report = audit_coverage(label.decision_at, rows, as_of,
                            horizon=label.deadline_at - label.decision_at)
    assert report.acceptable
    assert report.identity_status == "contiguous_ids"
    assert report.reason == "heuristic_pass_requires_independent_source_qa"
