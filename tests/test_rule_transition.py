from datetime import datetime, timedelta, timezone
import pytest
from research.exchange_rule_pit import RuleSnapshot
from research.rule_transition import audit_transition

T = datetime(2025, 1, 1, tzinfo=timezone.utc)


def snap(value, *, pub=T, cap=T, eff=T):
    return RuleSnapshot("binance", "XRPUSDT", "minNotional", value,
                        pub, cap, eff, "sha256:synthetic")


def check(items, before=T, after=T + timedelta(days=2)):
    return audit_transition(items, venue="binance", symbol="XRPUSDT",
                            rule="minNotional", before_at=before, after_at=after)


def test_change():
    t = T + timedelta(days=1)
    result = check([snap("10"), snap("20", pub=t, cap=t, eff=t)])
    assert (result["status"], result["changed"], result["ratio"]) == ("DATA_GO", True, "2")


def test_late_capture_not_visible_before():
    assert check([snap("10", cap=T + timedelta(days=1))])["status"] == "DATA_NO_GO"


def test_unchanged():
    assert check([snap("10")])["changed"] is False


def test_missing_evidence():
    assert check([])["reason"] == "missing_paired_pit_evidence"


def test_non_numeric():
    assert check([snap("unknown")])["reason"] == "non_numeric_rule"


def test_zero():
    assert check([snap("0")])["reason"] == "non_positive_or_nonfinite_rule"


def test_nan():
    assert check([snap("NaN")])["reason"] == "non_positive_or_nonfinite_rule"


def test_conflict():
    assert check([snap("10"), snap("20")])["status"] == "DATA_NO_GO"


def test_reversed_interval():
    with pytest.raises(ValueError):
        check([], before=T + timedelta(days=2), after=T)


def test_future_rule_not_visible():
    t = T + timedelta(days=3)
    assert check([snap("10"), snap("20", pub=t, cap=t, eff=t)])["changed"] is False
