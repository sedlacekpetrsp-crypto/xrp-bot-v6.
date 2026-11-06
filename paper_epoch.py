"""One-time PAPER account reset to a new epoch (owner request 2026-11-06).

Owner: bots whose strategy changed start again from 10 000 USDT. Nothing is deleted: the full previous
state is archived in `paper_epoch_resets`, and every old trade stays in its trades table. The reset
happens inside the bot's own locked tick (SELECT ... FOR UPDATE) and only when the account is flat,
so an open position is never abandoned. It runs at most once per bot (primary key).
Rollback: restore `archived_state` from `paper_epoch_resets` into the bot's state table.
"""
import json
from datetime import datetime, timezone

RESET_BOTS = frozenset({"LIQUIDITY_V2", "LH_WHALE"})
REASON = "Owner request 2026-11-06: new epoch from 10 000 USDT after strategy change; history archived, not deleted."
DDL = ("CREATE TABLE IF NOT EXISTS paper_epoch_resets (bot TEXT PRIMARY KEY, reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
       "archived_state JSONB NOT NULL, reason TEXT NOT NULL)")


def ensure_table(conn):
    conn.execute(DDL)


def maybe_reset(conn, bot, state, initial_fn, now_iso=None):
    """Return the state to use for this tick. Caller holds the state row lock."""
    if bot not in RESET_BOTS or state.get("position"):
        return state
    if conn.execute("SELECT 1 FROM paper_epoch_resets WHERE bot=%s", (bot,)).fetchone():
        return state
    done = conn.execute("INSERT INTO paper_epoch_resets (bot, archived_state, reason) VALUES (%s,%s::jsonb,%s) "
                        "ON CONFLICT (bot) DO NOTHING RETURNING bot", (bot, json.dumps(state), REASON)).fetchone()
    if not done:
        return state
    fresh = initial_fn()
    # keep signal bookkeeping so no already-seen candle is traded again after the reset
    fresh["seen"] = state.get("seen", 0)
    fresh["cooldown"] = state.get("cooldown", 0)
    fresh["epoch_started_at"] = now_iso or datetime.now(timezone.utc).isoformat()
    fresh["previous_epoch"] = {k: state.get(k) for k in ("balance", "count", "wins", "max_drawdown_pct", "activated_at")}
    print("PAPER EPOCH RESET", bot, json.dumps(fresh["previous_epoch"]), flush=True)
    return fresh
