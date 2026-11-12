"""Evidence gates for PAPER status reports (read-only, pure functions).

Dialog 0273 (G3) / 0276 / 0303. Separates layers that reports used to conflate:

  reachability   - the HTTP endpoint answered (200). Says nothing about workers.
  execution      - the worker's own last_cycle_at is recent.
  market_data    - the worker reports a fresh quote / non-blocked data.
  persistence    - what the endpoint can and cannot prove about DB writes.
  pause          - explicit pause from the served `paused_bots` list.

Rules (fail-safe, no false alarms):
  * Unreachable endpoint => every other layer UNKNOWN (not FAIL).
  * Missing field => UNKNOWN, never OK.
  * analysis.signal == "WAIT" is a normal no-signal state, never an alarm;
    persistence == "postgres" is a backend name, not an error.
  * An endpoint can never prove a DB write: best case is
    WORKER_CLAIMED_SAVE (LH-WHALE / LIQUIDITY set persistence="postgres" only
    after a successful save) or CONFIG_ONLY (value derived from env presence).
    DB freshness requires a SQL check, outside this module.
  * A bot absent from the payload is UNKNOWN, not "off". It is PAUSED only when
    listed in the served paused_bots.
  * Zero trades is not an alarm.
"""
from __future__ import annotations

from datetime import datetime, timezone

EXECUTION_MAX_AGE_S = 45.0
# Workers whose persistence flag is set by the runtime after a successful save.
RUNTIME_SAVE_FLAG = {"LH-WHALE", "LIQUIDITY"}
# Workers whose persistence flag is derived from configuration only.
CONFIG_ONLY_FLAG = {"FLY", "BEST-OF"}
PAUSE_NAMES = {"FLY": "FLY", "FAST": "FAST", "LEADLAG": "LEADLAG", "TV": "TV",
               "WHALE": "WHALE", "BEST-OF": "BEST"}


def _parse(ts) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None  # naive timestamps are not trusted
    return dt.astimezone(timezone.utc)


def worker_evidence(name: str, http_status, body, paused_bots, now: datetime) -> dict:
    """Classify one worker. `body` is that worker's sub-dict (or None)."""
    out = {"worker": name, "reachability": "REACHABLE" if http_status == 200 else "UNREACHABLE",
           "execution": "UNKNOWN", "market_data": "UNKNOWN", "persistence": "UNKNOWN",
           "pause": "UNKNOWN", "signal": None, "alarms": []}
    if http_status != 200:
        return out
    paused = paused_bots if isinstance(paused_bots, list) else None
    if paused is not None and name in PAUSE_NAMES:
        out["pause"] = "PAUSED_BY_CONFIG" if PAUSE_NAMES[name] in paused else "NOT_PAUSED"
    if not isinstance(body, dict):
        out["execution"] = "UNKNOWN_ABSENT_FROM_PAYLOAD"
        return out

    last = _parse(body.get("last_cycle_at"))
    if last is not None:
        age = (now - last).total_seconds()
        if age < 0:
            out["execution"] = "UNKNOWN_FUTURE_TIMESTAMP"
        else:
            out["execution"] = "OK" if age <= EXECUTION_MAX_AGE_S else "STALE"
            out["execution_age_s"] = round(age, 1)

    data_status = body.get("data_status")
    if data_status == "blocked" or body.get("data_error"):
        out["market_data"] = "BLOCKED"
    elif "market_price" in body:
        out["market_data"] = "FRESH" if body.get("market_price") is not None else "STALE"

    flag = body.get("persistence")
    if name in RUNTIME_SAVE_FLAG:
        if flag == "postgres" and out["execution"] == "OK":
            out["persistence"] = "WORKER_CLAIMED_SAVE"  # not SQL-verified
        elif flag in ("memory", "pending"):
            out["persistence"] = "NO_DB_SAVE_CLAIMED"
    elif name in CONFIG_ONLY_FLAG and flag is not None:
        out["persistence"] = "CONFIG_ONLY"

    analysis = body.get("analysis")
    if isinstance(analysis, dict) and isinstance(analysis.get("signal"), str):
        out["signal"] = analysis["signal"]  # informational; WAIT is normal

    err = body.get("last_error") or body.get("error")
    if err:
        out["alarms"].append("worker_error")
    if out["pause"] != "PAUSED_BY_CONFIG":
        if out["execution"] == "STALE":
            out["alarms"].append("execution_stale")
        if out["market_data"] == "BLOCKED":
            out["alarms"].append("market_data_blocked")
        if out["persistence"] == "NO_DB_SAVE_CLAIMED":
            out["alarms"].append("no_db_save_claimed")
    return out


def evidence_report(combined_health_http, combined_health_body, now: datetime,
                    workers=(("fly", "FLY"), ("fast", "FAST"), ("leadlag", "LEADLAG"),
                             ("tv_consensus", "TV"), ("whale", "WHALE"), ("bestof", "BEST-OF"),
                             ("lh_whale", "LH-WHALE"), ("liquidity_monitor", "LIQUIDITY"))) -> dict:
    body = combined_health_body if isinstance(combined_health_body, dict) else {}
    paused = body.get("paused_bots")
    rows = [worker_evidence(name, combined_health_http, body.get(key), paused, now)
            for key, name in workers]
    alarms = sorted(f"{r['worker']}:{a}" for r in rows for a in r["alarms"])
    return {"workers": rows, "alarms": alarms,
            "not_verifiable_here": ["db_write_freshness (needs SQL)",
                                    "heartbeat history (G1, no history stored)",
                                    "errors outside the sampled log window"]}


def significant_change(previous: dict | None, current: dict) -> bool:
    """Notify only when the alarm set changes (new or cleared), not every run."""
    prev = set((previous or {}).get("alarms", []))
    return prev != set(current.get("alarms", []))
