"""Claude review of research/rule_transition.py @ 27636d4 (PAPER, no PnL).

Strict xfail = known defect; after the fix remove the marker (XPASS fails)."""
from datetime import datetime, timedelta, timezone
import pytest
from research.exchange_rule_pit import RuleSnapshot
from research.rule_transition import audit_transition

T = datetime(2025, 1, 1, tzinfo=timezone.utc)
D = timedelta(days=1)


def snap(value, h, *, pub=T, cap=T, eff=T, symbol="XRPUSDT"):
    return RuleSnapshot("binance", symbol, "maxLeverage", value, pub, cap, eff, h)


def check(items, before, after, symbol="XRPUSDT"):
    return audit_transition(items, venue="binance", symbol=symbol,
                            rule="maxLeverage", before_at=before, after_at=after)


@pytest.mark.xfail(strict=True, reason="T1 MAJOR: one stale snapshot serves both legs -> DATA_GO changed=False")
def test_t1_same_evidence_both_legs_is_not_paired_evidence():
    # only one capture (Jan); real change effective June was archived only in November
    items = [snap("50", "h-jan"), snap("20", "h-jun", pub=T + 150 * D, cap=T + 300 * D, eff=T + 150 * D)]
    r = check(items, before=T + 60 * D, after=T + 240 * D)
    assert r["status"] == "DATA_NO_GO"   # today: DATA_GO, changed False (false 'unchanged')


@pytest.mark.xfail(strict=True, reason="T3 MINOR: output omits effective_at of both legs")
def test_t3_output_carries_effective_times():
    t = T + 10 * D
    # change effective day 10, captured day 20; before=day 15 still sees the old rule
    items = [snap("50", "a"), snap("20", "b", pub=t, cap=T + 20 * D, eff=t)]
    r = check(items, before=T + 15 * D, after=T + 25 * D)
    assert r["status"] == "DATA_GO" and r["changed"] is True
    assert r["after_effective_at"] == t.isoformat()


def test_t2_market_kind_still_absent():
    # R2 inherited: API has no market dimension at all (spot vs usdm cannot be expressed)
    import inspect
    assert "market" not in inspect.signature(audit_transition).parameters


def test_independent_hashes_and_change_detected():
    t = T + 5 * D
    r = check([snap("50", "a"), snap("20", "b", pub=t, cap=t, eff=t)], T + D, T + 6 * D)
    assert (r["changed"], r["before_evidence_hash"] != r["after_evidence_hash"]) == (True, True)


def test_symbol_isolated():
    t = T + 5 * D
    items = [snap("50", "a"), snap("20", "b", pub=t, cap=t, eff=t, symbol="BTCUSDT")]
    assert check(items, T + D, T + 6 * D)["changed"] is False


def test_infinity_rejected():
    assert check([snap("Infinity", "a")], T + D, T + 2 * D)["reason"] == "non_positive_or_nonfinite_rule"


def test_negative_rejected():
    assert check([snap("-5", "a")], T + D, T + 2 * D)["reason"] == "non_positive_or_nonfinite_rule"


def test_equal_interval_rejected():
    with pytest.raises(ValueError):
        check([], T + D, T + D)
