"""Claude review (dialog 0465) of afb2ca0/13e4bb3. Strict xfail = known defects, synthetic only."""
from datetime import datetime, timedelta, timezone

import pytest

from research.k11_event_independence import audit_independence

T = datetime(2026, 11, 20, tzinfo=timezone.utc)


def e(article="a", asset="XRP", announce=T, observed=T):
    return dict(article_id=article, asset=asset, announced_at=announce, observed_at=observed)


@pytest.mark.xfail(strict=True, reason="R1 MAJOR: observed_at == as_of accepted; strict PIT (Q16, e344063a) requires first_seen < decision")
def test_observation_at_cutoff_rejected_strict_pit():
    assert audit_independence([e(observed=T)], as_of=T)["accepted_indices"] == []


@pytest.mark.xfail(strict=True, reason="R2 MAJOR: article identity != event identity; a rescheduled/updated announcement of the same delisting counts as 2 independent articles (cf. E1 in 0443)")
def test_rescheduled_announcement_same_event_counts_once():
    x = audit_independence(
        [e("delist-xyz-v1", "XYZ"), e("delist-xyz-v2-reschedule", "XYZ", announce=T - timedelta(days=1), observed=T - timedelta(days=1))],
        as_of=T + timedelta(days=1), min_articles=2)
    assert x["independent_articles"] == 1


def test_same_timestamp_cluster_passes_gate_documented():
    # m3: 25 articles at one instant pass the gate; no temporal clustering / regime check.
    evs = [e(f"a{i}", announce=T, observed=T) for i in range(25)]
    assert audit_independence(evs, as_of=T + timedelta(seconds=1))["article_gate_ok"] is True


def test_rejections_carry_no_reason_documented():
    # m4: future-observed and duplicate rejections are indistinguishable in output.
    x = audit_independence([e("a"), e("a"), e("b", observed=T + timedelta(days=1))], as_of=T + timedelta(seconds=1))
    assert x["rejected_indices"] == [1, 2] and set(x) == {"accepted_indices", "rejected_indices", "independent_articles", "article_gate_ok"}
