"""READ-ONLY pre-deployment check of the Combined PAPER ledger for PR #5 (da2f665).

Standalone: needs only psycopg and DATABASE_URL, so it can run in a Render Shell on
the currently deployed commit. Opens a READ ONLY transaction, never writes, never
calls the network, prints no secrets. Usage:

    python tools/combined_ledger_precheck.py            # or paste the file and run it

It answers, for the stored ledger:
1. Would the first scan after deploying PR #5 trigger a rebalance that the old code
   would not (execution-month change)?
2. How much does the reported unrealized P/L change (old formula vs. new formula)?
3. Does equity - initial == realized + unrealized hold with the new formula?
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

DAY_MS = 86_400_000


def month(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m")


def analyse(ledger, now=None):
    now = now or datetime.now(timezone.utc)
    last_completed = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp() * 1000) - DAY_MS
    stored = ledger.get("last_rebalance_day")
    out = {"mode": ledger.get("mode"), "last_rebalance_day": stored,
           "last_rebalance_day_utc": month(stored) if stored else None,
           "positions": {s: {k: p.get(k) for k in ("qty", "entry", "entry_fee", "stop", "entry_at")}
                         for s, p in (ledger.get("positions") or {}).items()},
           "trade_count": len(ledger.get("trades") or []),
           "cash": ledger.get("cash"), "equity_stored": ledger.get("equity"),
           "realized_pnl_stored": ledger.get("realized_pnl"),
           "unrealized_pnl_stored_old_formula": ledger.get("unrealized_pnl")}
    if stored is None:
        out["rebalance_check"] = "no last_rebalance_day: both old and new code rebalance on first scan"
    else:
        old_now, old_stored = month(last_completed), month(stored)
        new_now, new_stored = month(last_completed + DAY_MS), month(stored + DAY_MS)
        out["rebalance_check"] = {
            "old_code_would_rebalance_now": old_now != old_stored,
            "new_code_would_rebalance_now": new_now != new_stored,
            "extra_rebalance_caused_by_pr5": (new_now != new_stored) and (old_now == old_stored)}
    fees_open = sum(float(p.get("entry_fee", 0)) for p in (ledger.get("positions") or {}).values())
    if ledger.get("unrealized_pnl") is not None:
        new_unreal = float(ledger["unrealized_pnl"]) - fees_open
        out["unrealized_pnl_new_formula_at_last_marks"] = new_unreal
        out["unrealized_change"] = -fees_open
        if ledger.get("equity") is not None and ledger.get("realized_pnl") is not None:
            init = float(ledger.get("initial_equity", 10000.0))
            out["identity_gap_new_formula"] = (float(ledger["equity"]) - init) - (float(ledger["realized_pnl"]) + new_unreal)
            out["identity_gap_old_formula"] = (float(ledger["equity"]) - init) - (float(ledger["realized_pnl"]) + float(ledger["unrealized_pnl"]))
    return out


def main():
    import psycopg
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL missing")
    with psycopg.connect(url, connect_timeout=10) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.combined_best_paper_state')")
            if cur.fetchone()[0] is None:
                print(json.dumps({"status": "TABLE_MISSING"})); return
            cur.execute("SELECT ledger, updated_at FROM combined_best_paper_state WHERE id=1")
            row = cur.fetchone()
    if row is None:
        print(json.dumps({"status": "NO_ROW"})); return
    report = {"status": "OK", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "updated_at": row[1].isoformat(), **analyse(row[0])}
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
