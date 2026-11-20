"""Claude review (run #93): 0426 cases P1-P4 adapted to strict lineage gate 16e926b,
plus new findings N1-N4 (strict xfail = known defect; flips to pass after fix)."""
import pytest
from research.pit_source_lineage_gate import gate

D = "2026-01-03T00:00:00Z"


def rec(origin, content_hash, parent=None, **kw):
    r = dict(origin_publisher=origin, archive_custodian="web.archive.org", source_id=origin,
             content_hash=content_hash, published_at="2026-01-01T00:00:00Z",
             captured_at="2026-01-02T00:00:00Z", claim_id="C1", derived_from=parent)
    r.update(kw)
    return r


def run(rows, **kw):
    return gate(rows, decision_at=D, claim_id="C1", **kw)


# --- 0426 P1-P4, same expectations, only import/record shape adapted ---
def test_p1_identical_content_across_origins_is_not_independent():
    assert run([rec("binance", "h1"), rec("coindesk", "h1")])["status"] == "DATA_NO_GO"


def test_p2_declared_upstream_collapses_to_root():
    assert run([rec("binance", "h1"), rec("coindesk", "h2", "binance")])["status"] == "DATA_NO_GO"


def test_p3_archive_host_is_custodian_not_origin():
    assert run([rec("binance", "h1"), rec("web.archive.org", "h1x")])["status"] == "DATA_NO_GO"


def test_p4_origin_aliases_count_once():
    r = run([rec("binance.com", "h1"), rec("www.binance.com", "h1")],
            aliases={"www.binance.com": "binance.com"})
    assert r["independent_origins"] == 1


# --- new findings ---
@pytest.mark.xfail(strict=True, reason="N1: declared verbatim republish (derived_from + same hash) "
                   "kills the whole claim instead of collapsing to its root")
def test_n1_declared_verbatim_copy_collapses_not_fails():
    r = run([rec("binance", "h1"), rec("coindesk", "h1", "binance"), rec("okx", "h3")])
    assert r["status"] == "DATA_GO" and r["independent_origins"] == 2


@pytest.mark.xfail(strict=True, reason="N2: content_hash not normalised (case) -> syndication missed")
def test_n2_hash_case_is_normalised():
    assert run([rec("a.com", "ABCDEF"), rec("b.com", "abcdef")])["status"] == "DATA_NO_GO"


@pytest.mark.xfail(strict=True, reason="N3: archive mirrors/variants not in exact-match host set")
@pytest.mark.parametrize("host", ["archive.is", "archive.li", "www.web.archive.org", "web.archive.org."])
def test_n3_archive_mirror_variants_rejected_as_origin(host):
    assert run([rec(host, "h1")])["reason"] == "archive_as_publisher"


@pytest.mark.xfail(strict=True, reason="N4: alias keys are not case-normalised although origins are")
def test_n4_alias_keys_case_insensitive():
    r = run([rec("www.a.com", "h1"), rec("a.com", "h1")], aliases={"WWW.A.com": "a.com"})
    assert r["independent_origins"] == 1


def test_untouched_declared_lineage_three_roots_without_copy():
    r = run([rec("binance", "h1"), rec("coindesk", "h2", "binance"), rec("okx", "h3")])
    assert r["status"] == "DATA_GO" and r["independent_origins"] == 2
