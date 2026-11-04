"""Durable, transactionally updated PAPER-only combined portfolio state."""
import json
import os

from research.combined_paper_execution import fresh, step


def _connect():
    import psycopg
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL missing: fail closed, do not reset PAPER portfolio")
    return psycopg.connect(url, connect_timeout=10)


def _ensure(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS combined_best_paper_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        ledger JSONB NOT NULL,
        snapshot JSONB,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""")


def read():
    with _connect() as conn:
        with conn.cursor() as cur:
            _ensure(cur)
            cur.execute("SELECT ledger, snapshot, updated_at FROM combined_best_paper_state WHERE id=1")
            row = cur.fetchone()
            if row is None:
                return {"status": "AWAITING_FIRST_SCAN", "persistence": "postgres"}
            return {"status": "RUNNING", "persistence": "postgres",
                    "paper_portfolio": row[0], "snapshot": row[1],
                    "updated_at": row[2].isoformat()}


def apply(snapshot, prices):
    """Serialize read-modify-write with row lock; rollback on any failure."""
    with _connect() as conn:
        with conn.cursor() as cur:
            _ensure(cur)
            cur.execute("""INSERT INTO combined_best_paper_state (id, ledger)
                           VALUES (1, %s::jsonb) ON CONFLICT (id) DO NOTHING""",
                        (json.dumps(fresh()),))
            cur.execute("SELECT ledger FROM combined_best_paper_state WHERE id=1 FOR UPDATE")
            previous = cur.fetchone()[0]
            if previous.get("mode") != "PAPER_ONLY":
                raise ValueError("Unexpected portfolio mode")
            ledger = step(previous, snapshot["last_completed_day"],
                          snapshot["candidates"], prices)
            snapshot = dict(snapshot, paper_portfolio=ledger,
                            note="Simulated PAPER fills only; no exchange orders.")
            cur.execute("""UPDATE combined_best_paper_state
                           SET ledger=%s::jsonb, snapshot=%s::jsonb, updated_at=NOW()
                           WHERE id=1""", (json.dumps(ledger), json.dumps(snapshot)))
        conn.commit()
    return snapshot
