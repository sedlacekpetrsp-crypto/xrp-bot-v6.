"""Synthetic tests for report evidence gates (dialog 0303). No network."""
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "tools/autopilot")
from evidence_gates import evidence_report, significant_change, worker_evidence  # noqa: E402

NOW = datetime(2026, 11, 12, 6, 0, tzinfo=timezone.utc)
PAUSED = ["BEST", "FAST", "FLY", "LEADLAG", "TV", "WHALE"]


def lh(age_s=10, persistence="postgres", signal="WAIT", **kw):
    b = dict(last_cycle_at=(NOW - timedelta(seconds=age_s)).isoformat(), persistence=persistence,
             data_status="ok", market_price=0.55, analysis={"signal": signal},
             last_error=None, data_error=None, trades_count=0)
    b.update(kw)
    return b


def test_wait_postgres_is_not_an_alarm():
    r = worker_evidence("LH-WHALE", 200, lh(), PAUSED, NOW)
    assert r["alarms"] == [] and r["signal"] == "WAIT"
    assert r["persistence"] == "WORKER_CLAIMED_SAVE"  # never "DB verified"


def test_http_200_alone_proves_nothing_about_worker():
    r = worker_evidence("LIQUIDITY", 200, {}, PAUSED, NOW)
    assert (r["execution"], r["market_data"], r["persistence"]) == ("UNKNOWN",) * 3


def test_unreachable_is_unknown_not_fail():
    r = worker_evidence("LH-WHALE", None, lh(), PAUSED, NOW)
    assert r["reachability"] == "UNREACHABLE" and r["execution"] == "UNKNOWN" and r["alarms"] == []


def test_stale_cycle_and_postgres_flag_do_not_claim_save():
    r = worker_evidence("LH-WHALE", 200, lh(age_s=120), PAUSED, NOW)
    assert r["execution"] == "STALE" and r["persistence"] == "UNKNOWN"
    assert "execution_stale" in r["alarms"]


def test_memory_persistence_alarm_and_config_only_flag():
    assert "no_db_save_claimed" in worker_evidence("LIQUIDITY", 200, lh(persistence="memory"), PAUSED, NOW)["alarms"]
    fly = worker_evidence("FLY", 200, {"persistence": "postgres", "last_cycle_at": None}, PAUSED, NOW)
    assert fly["persistence"] == "CONFIG_ONLY"


def test_absent_bot_is_unknown_not_off_and_pause_needs_explicit_list():
    r = worker_evidence("LEADLAG", 200, None, PAUSED, NOW)
    assert r["pause"] == "PAUSED_BY_CONFIG" and r["execution"] == "UNKNOWN_ABSENT_FROM_PAYLOAD"
    assert worker_evidence("LEADLAG", 200, None, None, NOW)["pause"] == "UNKNOWN"
    assert worker_evidence("FLY", 200, {}, ["TV"], NOW)["pause"] == "NOT_PAUSED"


def test_paused_bot_stale_is_not_alarmed():
    r = worker_evidence("FAST", 200, {"last_cycle_at": (NOW - timedelta(hours=5)).isoformat()}, PAUSED, NOW)
    assert r["execution"] == "STALE" and r["alarms"] == []


def test_liquidity_and_lh_whale_classified_independently():
    body = {"paused_bots": PAUSED, "lh_whale": lh(), "liquidity_monitor": lh(last_error="Timeout")}
    rep = evidence_report(200, body, NOW)
    assert rep["alarms"] == ["LIQUIDITY:worker_error"]


def test_naive_or_future_timestamps_not_trusted():
    assert worker_evidence("LH-WHALE", 200, lh(last_cycle_at="2026-11-12T05:59:50"), PAUSED, NOW)["execution"] == "UNKNOWN"
    fut = lh(last_cycle_at=(NOW + timedelta(minutes=5)).isoformat())
    assert worker_evidence("LH-WHALE", 200, fut, PAUSED, NOW)["execution"] == "UNKNOWN_FUTURE_TIMESTAMP"


def test_blocked_data_alarm():
    assert "market_data_blocked" in worker_evidence("LH-WHALE", 200, lh(data_status="blocked"), PAUSED, NOW)["alarms"]


def test_notify_only_on_alarm_set_change():
    a = {"alarms": []}
    b = {"alarms": ["LIQUIDITY:worker_error"]}
    assert not significant_change(a, {"alarms": []})
    assert significant_change(a, b) and significant_change(b, a)
    assert not significant_change(b, {"alarms": ["LIQUIDITY:worker_error"]})
