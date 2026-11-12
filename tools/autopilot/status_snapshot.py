"""Read-only snapshot of the public PAPER status endpoints (runs in GitHub Actions).

GET only, no credentials, no writes. Prints one line `AUTOPILOT_SUMMARY {...}` with the
key facts and writes the raw responses to status_raw.json (uploaded as an artifact).
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, "tools")
from combined_ledger_precheck import analyse  # noqa: E402
sys.path.insert(0, "tools/autopilot")
from evidence_gates import evidence_report  # noqa: E402

BASE = "https://xrp-fly-whale-24-7.onrender.com"
PATHS = ("/health", "/combined/health", "/combined/status", "/elite-paper/status",
         "/swing/status", "/news-paper/status")
START = 10_000.0


def get(path):
    t0 = time.time()
    try:
        with urllib.request.urlopen(BASE + path, timeout=60) as r:
            return r.status, json.loads(r.read().decode()), round(time.time() - t0, 3)
    except Exception as exc:  # recorded, never hidden
        return None, {"error": type(exc).__name__ + ": " + str(exc)}, round(time.time() - t0, 3)


def code_markers():
    """Text markers in the served dashboard that identify deployed code versions."""
    try:
        with urllib.request.urlopen(BASE + "/", timeout=60) as r:
            html = r.read().decode(errors="replace")
    except Exception as exc:
        return {"error": type(exc).__name__}
    return {"trendline_risk_0_1pct": "cílové riziko 0,1 %" in html,
            "trendline_risk_3pct": "cílové riziko 3 %" in html, "dashboard_bytes": len(html)}


def main():
    now = datetime.now(timezone.utc)
    raw = {p: dict(zip(("http", "body", "seconds"), get(p))) for p in PATHS}
    raw["fetched_at_utc"] = now.isoformat()
    json.dump(raw, open("status_raw.json", "w"), indent=1)
    h = raw["/health"]["body"]; ch = raw["/combined/health"]["body"]
    cs = raw["/combined/status"]["body"]; el = raw["/elite-paper/status"]["body"]
    sw = raw["/swing/status"]["body"]; nw = raw["/news-paper/status"]["body"]
    accounts = {}
    def put(name, balance, trades=None, healthy=None, err=None):
        if balance is not None:
            accounts[name] = dict(net=round(float(balance) - START, 2), trades=trades, healthy=healthy, error=err)
    for key, name in (("fly", "FLY"), ("whale", "WHALE"), ("fast", "FAST"), ("tv_consensus", "TV"),
                      ("bestof", "BEST-OF"), ("leadlag", "LEADLAG"), ("lh_whale", "LH-WHALE"),
                      ("liquidity_monitor", "LIQUIDITY")):
        b = (ch or {}).get(key) or {}
        t = b.get("trades_count", b.get("trades") if isinstance(b.get("trades"), int) else None)
        if name == "FLY":
            t = (b.get("stats") or {}).get("count")
        put(name, b.get("balance"), t, b.get("healthy"), b.get("last_error") or b.get("error"))
    for a in (sw or {}).get("accounts", []):
        put(a["id"].upper(), a.get("balance"), a.get("trades_count"), a.get("healthy"), a.get("last_error"))
    put("NEWS_LONG", (nw or {}).get("balance"), (nw or {}).get("trades_count"), (nw or {}).get("healthy"), (nw or {}).get("last_error"))
    for k, a in ((el or {}).get("accounts") or {}).items():
        put("ELITE_" + k, a.get("equity"), a.get("trades"), (el or {}).get("healthy"), (el or {}).get("last_error"))
    pp = (cs or {}).get("paper_portfolio") or {}
    put("COMBINED", pp.get("equity"), pp.get("trade_count"), (cs or {}).get("status") == "RUNNING", (cs or {}).get("error"))
    uptime = (h or {}).get("uptime_seconds")
    summary = {
        "fetched_at_utc": now.isoformat(),
        "http": {p: raw[p]["http"] for p in PATHS},
        "process_started_utc": datetime.fromtimestamp(now.timestamp() - uptime, timezone.utc).isoformat() if uptime else None,
        "paused_bots": (ch or {}).get("paused_bots"),
        "accounts": accounts,
        "total_net": round(sum(a["net"] for a in accounts.values()), 2),
        "combined_ledger_check": analyse(pp, now) if pp else None,
        "combined_updated_at": (cs or {}).get("updated_at"),
        "code_markers": code_markers(),
        "evidence": evidence_report(raw["/combined/health"]["http"], ch, now),
        "elite_last_tick_ms": max([a.get("last_tick") or 0 for a in ((el or {}).get("accounts") or {}).values()] or [0]),
    }
    print("AUTOPILOT_SUMMARY " + json.dumps(summary, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
