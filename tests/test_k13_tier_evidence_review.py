"""Independent review tests (Claude) for research/k13_tier_evidence.py @ fc1d055.
strict xfail = documented defect; flips to XPASS (fail) once fixed."""
import pytest
from research.k13_tier_evidence import tier_change_evidence


def rec(**kw):
    r = dict(venue="Binance", market="usdt_perpetual", symbol="XRPUSDT", tier=1,
             source_id="archive-001", before={"max_leverage": "50"}, after={"max_leverage": "25"})
    r.update(kw)
    return r


def test_valid_baseline_still_ok():
    assert tier_change_evidence(rec())["ok"]


@pytest.mark.xfail(strict=True, reason="E1 MAJOR: no as-of timestamps / capture provenance; PIT not checkable")
def test_e1_missing_provenance_fail_closed():
    # record without before_as_of/after_as_of/url/sha256 must not be ok
    assert tier_change_evidence(rec())["reason"] == "missing_provenance"


@pytest.mark.xfail(strict=True, reason="E2 MAJOR: reversed order before/after undetectable")
def test_e2_reversed_order_rejected():
    r = rec(before_as_of="2024-05-02T00:00:00Z", after_as_of="2024-05-01T00:00:00Z")
    assert not tier_change_evidence(r)["ok"]


@pytest.mark.xfail(strict=True, reason="E3 MAJOR: tier renumbering (bracket shift) counted as change")
def test_e3_tier_identity_needs_bracket_bounds():
    # same tier number, but notional floor moved => different bracket, not same-tier change
    r = rec(before={"max_leverage": "50", "notional_cap": "50000"},
            after={"max_leverage": "25", "notional_cap": "10000"})
    r["before_floor"], r["after_floor"] = "0", "5000"
    assert tier_change_evidence(r)["reason"] == "tier_identity_changed"


@pytest.mark.xfail(strict=True, reason="E4 MINOR: MMR unit ambiguity (percent vs fraction) => false change")
def test_e4_mmr_unit_out_of_range():
    r = rec(before={"maintenance_margin_rate": "0.5"}, after={"maintenance_margin_rate": "0.005"})
    # 0.5 (meant %) vs 0.005 (fraction) are the same rule; rate must be in (0, 0.5] fraction with explicit unit
    assert not tier_change_evidence(r)["ok"]


@pytest.mark.xfail(strict=True, reason="E5 MINOR: venue/symbol not normalized => clustering splits episodes")
def test_e5_identity_normalized():
    a = tier_change_evidence(rec(venue="binance ", symbol="xrpusdt"))
    assert a.get("venue") == "binance" and a.get("symbol") == "XRPUSDT"
