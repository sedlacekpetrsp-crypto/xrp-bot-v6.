"""Regresní test BEST-OF: stejná otevřená pozice se do bestof_trades zapíše právě jednou.

Spouští skutečný kód app_bestof_core.save_trade proti skutečnému PostgreSQL:
- opakované zpracování (stejné uzavření 2x za sebou),
- překrývající se běhy (8 vláken = 8 "instancí" současně, s uměle rozšířeným oknem
  mezi kontrolou a zápisem),
- atomicita: advisory zámek drží celou transakci, chyba uprostřed nezanechá řádek
  ani zámek,
- kontrola síly testu: bez advisory zámku stejný scénář duplikát skutečně vytvoří.

Potřebuje PostgreSQL v proměnné BESTOF_PG_TEST_DSN (např. postgresql://postgres@/postgres?host=/tmp&port=55432).
Bez ní se test přeskočí. Používá psycopg, pokud je nainstalovaný (produkční závislost);
jinak tenkou náhradu přes `psql` (jen pro sandbox bez PyPI). Výhradně testovací DB.
"""
import os
import subprocess
import sys
import threading
import time
import types
import unittest
import uuid
from unittest.mock import patch

DSN = os.getenv("BESTOF_PG_TEST_DSN")

try:  # produkční ovladač (nainstalovaný balík, ne testovací stub)
    import psycopg  # noqa: F401
    _pf = getattr(psycopg, "__file__", "") or ""
    HAVE_PSYCOPG = ("site-packages" in _pf or "dist-packages" in _pf)
except ImportError:  # sandbox bez PyPI: stub jen kvůli importu modulu
    HAVE_PSYCOPG = False
    sys.modules.setdefault("psycopg", types.ModuleType("psycopg"))
if os.getenv("BESTOF_PG_TEST_DRIVER") == "psql":
    HAVE_PSYCOPG = False
for _name in ("httpx",):
    try:
        __import__(_name)
    except ImportError:
        sys.modules.setdefault(_name, types.ModuleType(_name))
try:
    import fastapi  # noqa: F401
except ImportError:  # sandbox bez PyPI: modul jen definuje routy, test je nevolá
    class _App:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, _):
            return lambda *a, **k: (lambda f: f)

    _fa = types.ModuleType("fastapi")
    _fa.FastAPI = _App
    _fr = types.ModuleType("fastapi.responses")
    _fr.HTMLResponse = _fr.Response = object
    sys.modules.setdefault("fastapi", _fa)
    sys.modules.setdefault("fastapi.responses", _fr)

import app_bestof_core as core  # noqa: E402


# ---------------------------------------------------------------- psql náhrada
class _PsqlCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params=None):
        self.rows = self.conn._run(_interpolate(query, params))

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


def _lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    tag = "q" + uuid.uuid4().hex[:8]
    return f"${tag}${v}${tag}$"


def _interpolate(query, params):
    if not params:
        return query
    parts = query.split("%s")
    assert len(parts) == len(params) + 1, "počet %s neodpovídá parametrům"
    out = parts[0]
    for p, rest in zip(params, parts[1:]):
        out += _lit(p) + rest
    return out


class PsqlConnection:
    """Minimum psycopg API (transakce jako psycopg: BEGIN implicitně, commit/rollback)."""

    END = "__END_OF_STATEMENT__"

    def __init__(self, dsn):
        self.p = subprocess.Popen(
            ["psql", "-X", "-q", "-A", "-t", "-F", "\x1f", "-v", "ON_ERROR_STOP=0", dsn],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        self.in_tx = False

    def _raw(self, sql):
        self.p.stdin.write(sql.rstrip().rstrip(";") + ";\n\\echo " + self.END + "\n")
        self.p.stdin.flush()
        rows, err = [], None
        for line in self.p.stdout:
            line = line.rstrip("\n")
            if line == self.END:
                break
            if line.startswith("ERROR:") or line.startswith("psql:"):
                err = err or line
            elif line:
                rows.append(tuple(line.split("\x1f")))
        if err:
            raise RuntimeError(err)
        return rows

    def _run(self, sql):
        if not self.in_tx:
            self._raw("BEGIN")
            self.in_tx = True
        try:
            return self._raw(sql)
        except Exception:
            self.rollback()
            raise

    def cursor(self):
        return _PsqlCursor(self)

    def commit(self):
        if self.in_tx:
            self._raw("COMMIT")
            self.in_tx = False

    def rollback(self):
        if self.in_tx:
            self._raw("ROLLBACK")
            self.in_tx = False

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *a):  # chování jako psycopg 3: commit / rollback, pak zavřít
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False


def connect(dsn=DSN):
    if HAVE_PSYCOPG:
        import psycopg
        return psycopg.connect(dsn)
    return PsqlConnection(dsn)


# ---------------------------------------------------------------- pomocné
TABLE = "bestof_trades"
OPENED = "2026-11-05T08:20:29.773893+00:00"


def trade(**kw):
    t = dict(symbol="XRPUSDT", side="LONG", setup="BREAKOUT", entry_market=1.3227,
             entry_price=1.32296454, exit_market=1.3151, exit_price=1.31483698,
             qty=1091.9, gross_pnl=-8.3, slippage=0.58, fees=1.44, pnl=-10.31,
             reason="STOP LOSS", opened_at=OPENED,
             closed_at="2026-11-05T09:14:07.761682+00:00")
    t.update(kw)
    return t


def scalar(sql):
    with connect() as c:
        with c.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]


def rows_for(opened=OPENED):
    return int(scalar(f"SELECT count(*) FROM {TABLE} WHERE opened_at = '{opened}'::timestamptz"))


class SlowCursor:
    """Obal kurzoru: po kontrolní SELECT rozšíří okno souběhu (simulace pomalé instance)."""

    def __init__(self, cur, delay, drop_lock):
        self.cur, self.delay, self.drop_lock = cur, delay, drop_lock

    def __enter__(self):
        self.cur.__enter__()
        return self

    def __exit__(self, *a):
        return self.cur.__exit__(*a)

    def execute(self, q, params=None):
        if self.drop_lock and "pg_advisory_xact_lock" in q:
            return None  # kontrola síly testu: stejný kód bez zámku
        r = self.cur.execute(q, params)
        if q.lstrip().startswith("SELECT id FROM"):
            time.sleep(self.delay)
        return r

    def fetchone(self):
        return self.cur.fetchone()


class SlowConn:
    def __init__(self, delay=0.3, drop_lock=False):
        self.c, self.delay, self.drop_lock = connect(), delay, drop_lock

    def __enter__(self):
        self.c.__enter__()
        return self

    def __exit__(self, *a):
        return self.c.__exit__(*a)

    def cursor(self):
        return SlowCursor(self.c.cursor(), self.delay, self.drop_lock)

    def commit(self):
        self.c.commit()


def overlapping(n, delay, drop_lock=False, **kw):
    barrier = threading.Barrier(n)
    results, errors = [], []

    def worker(i):
        try:
            barrier.wait(timeout=30)
            results.append(core.save_trade(trade(closed_at=f"2026-11-05T09:14:{10 + i:02d}+00:00", **kw)))
        except Exception as e:  # pragma: no cover
            errors.append(e)

    with patch.object(core, "get_db", lambda: SlowConn(delay, drop_lock)):
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
    return results, errors


@unittest.skipUnless(DSN, "BESTOF_PG_TEST_DSN není nastaveno - test proti PostgreSQL přeskočen")
class BestofDedupePostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.multiple(core, DATABASE_URL=DSN, get_db=connect):
            core.init_db()

    def setUp(self):
        self.p = patch.multiple(core, DATABASE_URL=DSN, get_db=connect)
        self.p.start()
        with connect() as c:
            with c.cursor() as cur:
                cur.execute(f"TRUNCATE {TABLE}")

    def tearDown(self):
        self.p.stop()

    def test_repeated_processing_saves_once(self):
        self.assertTrue(core.save_trade(trade()))
        self.assertFalse(core.save_trade(trade(closed_at="2026-11-05T09:14:10.872418+00:00")))
        self.assertFalse(core.save_trade(trade()))
        self.assertEqual(rows_for(), 1)

    def test_different_openings_are_all_saved(self):
        self.assertTrue(core.save_trade(trade()))
        self.assertTrue(core.save_trade(trade(opened_at="2026-11-05T10:20:00+00:00")))
        self.assertTrue(core.save_trade(trade(setup="PULLBACK")))
        self.assertTrue(core.save_trade(trade(symbol="SOLUSDT")))
        self.assertEqual(int(scalar(f"SELECT count(*) FROM {TABLE}")), 4)

    def test_overlapping_instances_close_same_position_once(self):
        results, errors = overlapping(8, delay=0.3)
        self.assertEqual(errors, [])
        self.assertEqual(sorted(results), [False] * 7 + [True])
        self.assertEqual(rows_for(), 1)

    def test_without_lock_the_same_race_duplicates(self):
        # Kontrola, že předchozí test má sílu: stejný souběh bez zámku duplikát vytvoří.
        results, errors = overlapping(8, delay=0.3, drop_lock=True)
        self.assertEqual(errors, [])
        self.assertGreater(rows_for(), 1)

    def test_lock_is_held_for_whole_transaction(self):
        seen = {}

        def probe():
            time.sleep(0.15)  # během okna mezi SELECT a INSERT druhé "instance"
            seen["locks"] = int(scalar(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted "
                f"AND classid = {core.TRADE_WRITE_LOCK[0]} AND objid = {core.TRADE_WRITE_LOCK[1]}"))

        t = threading.Thread(target=probe)
        with patch.object(core, "get_db", lambda: SlowConn(0.5)):
            t.start()
            self.assertTrue(core.save_trade(trade()))
        t.join()
        self.assertEqual(seen["locks"], 1)
        self.assertEqual(int(scalar("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'")), 0)

    def test_failure_inside_transaction_leaves_no_row_and_releases_lock(self):
        bad = trade(symbol=None)  # NOT NULL -> chyba při INSERT uvnitř transakce
        self.assertFalse(core.save_trade(bad))
        self.assertEqual(int(scalar(f"SELECT count(*) FROM {TABLE}")), 0)
        self.assertEqual(int(scalar("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'")), 0)
        self.assertTrue(core.save_trade(trade()))  # zámek uvolněn, další zápis projde
        self.assertEqual(rows_for(), 1)


if __name__ == "__main__":
    unittest.main()
