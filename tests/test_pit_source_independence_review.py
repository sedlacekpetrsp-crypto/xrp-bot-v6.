"""Claude review 0426: false-independence cases (strict xfail = known defect)."""
import pytest
from research.pit_source_independence import independent_source_gate

T = "2026-01-03T00:00:00Z"


def rec(origin, source_id, content_hash="abc", **kw):
    r = dict(origin=origin, source_id=source_id, content_hash=content_hash,
             published_at="2026-01-01T00:00:00Z", captured_at="2026-01-02T00:00:00Z")
    r.update(kw)
    return r


@pytest.mark.xfail(strict=True, reason="P1: identical bytes from two 'origins' = syndication, counted as 2")
def test_identical_content_across_origins_is_not_independent():
    rows = [rec("binance", "a", "h1"), rec("coindesk", "b", "h1")]
    assert independent_source_gate(rows, decision_at=T)["status"] == "DATA_NO_GO"


@pytest.mark.xfail(strict=True, reason="P2: no lineage field; republished primary counted as independent")
def test_declared_upstream_collapses_to_root():
    rows = [rec("binance", "a", "h1"), rec("coindesk", "b", "h2", derived_from="binance")]
    assert independent_source_gate(rows, decision_at=T)["status"] == "DATA_NO_GO"


@pytest.mark.xfail(strict=True, reason="P3: archive host accepted as origin publisher")
def test_archive_host_is_custodian_not_origin():
    rows = [rec("binance", "a", "h1"), rec("web.archive.org", "b", "h1x")]
    assert independent_source_gate(rows, decision_at=T)["status"] == "DATA_NO_GO"


@pytest.mark.xfail(strict=True, reason="P4: origin aliases (domain vs name) not canonicalised")
def test_origin_aliases_count_once():
    rows = [rec("binance.com", "a", "h1"), rec("www.binance.com", "b", "h1")]
    assert independent_source_gate(rows, decision_at=T)["independent_origins"] == 1


def test_dedup_within_origin_still_ok():
    rows = [rec("binance", "a"), rec("Binance ", "b")]
    assert independent_source_gate(rows, decision_at=T)["independent_origins"] == 1
