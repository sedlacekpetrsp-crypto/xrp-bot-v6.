"""Claude review (dialog 0418) of research/exchange_rule_pit.py @ d7a1d7b.

Pins behaviour that the review considers wrong. Tests marked xfail(strict=True)
describe the REQUIRED behaviour; they flip to XPASS (= failure under strict) once
the module is fixed, so the fixer must remove the marker. PAPER only, no prices.
"""
from datetime import datetime, timezone, timedelta
import pytest
from research.exchange_rule_pit import RuleSnapshot, rule_asof

T = datetime(2024, 1, 1, tzinfo=timezone.utc)
D = timedelta(days=1)


def snap(value, *, pub, cap, eff, venue="binance", symbol="XRPUSDT", h=None):
    return RuleSnapshot(venue, symbol, "minNotional", value, pub, cap, eff,
                        h or f"sha256:{value}:{cap.isoformat()}")


def q(items, at, venue="binance", symbol="XRPUSDT"):
    return rule_asof(items, venue=venue, symbol=symbol, rule="minNotional",
                     decision_at=at)


# R1 (MAJOR): stale evidence is returned as DATA_GO although the rule in force
# changed before the decision (change archived only later). For a realizability
# audit the question is "which rule applied at decision", not only "what had we
# archived"; without a capture fresh enough to rule out a change, fail closed.
@pytest.mark.xfail(strict=True, reason="R1: no staleness bound -> stale value DATA_GO")
def test_stale_evidence_must_fail_closed():
    a = snap("10", pub=T, cap=T, eff=T)                       # known in Jan
    b = snap("20", pub=T + 150 * D, cap=T + 330 * D, eff=T + 152 * D)  # change Jun, archived Nov
    r = q([a, b], at=T + 250 * D)                             # decision Sep
    assert r["status"] == "DATA_NO_GO"                        # today: DATA_GO value "10" (wrong rule)


def test_current_behaviour_returns_stale_value():
    a = snap("10", pub=T, cap=T, eff=T)
    b = snap("20", pub=T + 150 * D, cap=T + 330 * D, eff=T + 152 * D)
    r = q([a, b], at=T + 250 * D)
    assert (r["status"], r["value"]) == ("DATA_GO", "10")


# R2 (MAJOR): one `venue` string for spot and USDT-M futures. Binance spot
# (api/v3 exchangeInfo NOTIONAL filter) and USDT-M (fapi/v1 MIN_NOTIONAL
# `notional`) are different instruments with different rules under one symbol.
@pytest.mark.xfail(strict=True, reason="R2: no market dimension -> spot rule served for futures")
def test_spot_snapshot_must_not_answer_futures_query():
    spot = snap("1", pub=T, cap=T + D, eff=T + D)          # spot NOTIONAL 1 USDT (later)
    fut = snap("5", pub=T, cap=T, eff=T)                    # USDT-M notional 5 USDT
    r = q([spot, fut], at=T + 2 * D)
    assert r.get("value") == "5"                            # today: "1" (spot leaks into futures)


# R3 (MINOR): same evidence_hash with different content is not detected.
@pytest.mark.xfail(strict=True, reason="R3: duplicate evidence_hash with different value accepted")
def test_hash_reuse_with_different_value_rejected():
    a = snap("10", pub=T, cap=T, eff=T - D, h="sha256:same")
    b = snap("20", pub=T, cap=T, eff=T, h="sha256:same")
    with pytest.raises(ValueError):
        q([a, b], at=T + D)


# R4 (MINOR): symbol/venue matching is case-sensitive -> silent DATA_NO_GO
# instead of explicit normalisation or ValueError.
def test_case_mismatch_is_silent_no_go():
    r = q([snap("10", pub=T, cap=T, eff=T, symbol="xrpusdt")], at=T)
    assert r == {"status": "DATA_NO_GO", "reason": "no_pit_evidence"}
