"""Regression: coverage QA must use the label's own horizon (growth 720h vs downside 336h)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from research.early_growth_radar_v1.label_events import label_decision as growth_label
from research.top_risk_radar_v1.coverage_qa import audit_coverage, audit_label_coverage
from research.top_risk_radar_v1.label_events import Trade, label_decision as downside_label

D = datetime(2024, 1, 2, 0, 5, tzinfo=timezone.utc)
FOURTEEN_DAYS = [Trade(D + timedelta(minutes=i), Decimal("1"), i) for i in range(14 * 24 * 60 + 1)]
AS_OF = D + timedelta(days=31)


def test_growth_negative_with_only_14_days_fails_label_bound_coverage():
    label = growth_label(D, FOURTEEN_DAYS, AS_OF)
    assert label.status == "negative_requires_coverage_qa"
    # Generic default horizon would wrongly accept it:
    assert audit_coverage(D, FOURTEEN_DAYS, AS_OF).acceptable
    assert not audit_label_coverage(label, FOURTEEN_DAYS, AS_OF).acceptable


def test_downside_label_bound_coverage_matches_336h():
    label = downside_label(D, FOURTEEN_DAYS, AS_OF)
    assert label.status == "negative_requires_coverage_qa"
    assert audit_label_coverage(label, FOURTEEN_DAYS, AS_OF).acceptable
