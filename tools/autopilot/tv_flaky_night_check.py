"""Run the TV daily-pause test with utcnow frozen at several UTC times (incl. 00:00-02:00).
Usage: python tools/autopilot/tv_flaky_night_check.py  -> prints NIGHTCHECK lines, exit 1 on failure."""
import datetime as dt, importlib, sys, unittest
sys.path.insert(0, '.')
NAME = 'test_tv_consensus.RiskTests.test_daily_pause_disabled_allows_entry_without_resetting_losses'
TIMES = [(23, 59, 59), (0, 0, 0), (0, 0, 1), (0, 10, 0), (0, 19, 59), (0, 20, 1), (0, 30, 0),
         (1, 59, 0), (2, 1, 0), (13, 0, 0), (23, 59, 0)]
bad = 0
for _rep in range(2):  # repeated runs: no state leaks between runs
    for h, m, s in TIMES:
        fixed = dt.datetime(2026, 11, 8, h, m, s, tzinfo=dt.timezone.utc)
        import tv_consensus_scalper as tv
        tv.utcnow = lambda f=fixed: f
        import test_tv_consensus as T
        importlib.reload(T); T.tv.utcnow = lambda f=fixed: f
        r = unittest.TextTestRunner(verbosity=0, stream=open('/dev/null', 'w')).run(unittest.TestLoader().loadTestsFromName(NAME))
        ok = r.wasSuccessful(); bad += not ok
        print(f"NIGHTCHECK {h:02d}:{m:02d}:{s:02d} {'OK' if ok else 'FAIL'}")
        for _, tb in r.failures + r.errors:
            print(tb.splitlines()[-1])
sys.exit(1 if bad else 0)
