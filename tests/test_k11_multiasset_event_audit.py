"""Synthetic tests only: no market data and no performance execution."""
from research.k11_multiasset_event_audit import audit_multiasset_events


def event(asset="AAA", cms_id="123", url="https://example.org/article", effective="2026-01-03T12:00:00Z", published="2026-01-02T12:00:00Z"):
    return dict(asset=asset, cms_id=cms_id, source_url=url,
                effective_at=effective, published_at=published)


def test_one_announcement_two_assets():
    r = audit_multiasset_events([event("AAA"), event("BBB")])
    assert r["unique_events"] == 2
    assert r["unique_announcements"] == 1
    assert not r["rejected"]


def test_same_asset_same_effective_is_duplicate():
    r = audit_multiasset_events([event(), event()])
    assert r["unique_events"] == 1
    assert "duplicate" in r["rejected"][0]["reason"]


def test_conflicting_cms_mapping_rejected():
    r = audit_multiasset_events([event(), event("BBB", url="https://example.org/other")])
    assert r["unique_events"] == 1
    assert "conflicting" in r["rejected"][0]["reason"]


def test_conflicting_url_mapping_rejected():
    r = audit_multiasset_events([event(), event("BBB", cms_id="456")])
    assert r["unique_events"] == 1
    assert "conflicting" in r["rejected"][0]["reason"]


def test_different_announcement_same_asset_effective_deduped():
    r = audit_multiasset_events([event(), event(cms_id="456", url="https://example.org/other")])
    assert r["unique_events"] == 1


def test_timezone_equivalent_effective_deduped():
    r = audit_multiasset_events([event(), event(effective="2026-01-03T13:00:00+01:00")])
    assert r["unique_events"] == 1


def test_reject_publication_at_effective():
    r = audit_multiasset_events([event(published="2026-01-03T12:00:00Z")])
    assert r["unique_events"] == 0


def test_reject_naive_timestamp():
    r = audit_multiasset_events([event(published="2026-01-02T12:00:00")])
    assert r["unique_events"] == 0


def test_reject_credentials_in_url():
    r = audit_multiasset_events([event(url="https://user:secret@example.org/article")])
    assert r["unique_events"] == 0


def test_reject_bool_cms_id():
    r = audit_multiasset_events([event(cms_id=True)])
    assert r["unique_events"] == 0


def test_rejected_record_does_not_poison_future_identity():
    r = audit_multiasset_events([event(published="2026-01-03T12:00:00Z"), event()])
    assert r["accepted_indices"] == [1]


def test_reject_non_mapping():
    r = audit_multiasset_events([None, event()])
    assert r["accepted_indices"] == [1]
