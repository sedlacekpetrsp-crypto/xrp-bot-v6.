"""Run the TV daily-pause test with utcnow frozen at several UTC times (incl. 00:00-02:00).
Usage: python tools/autopilot/tv_flaky_night_check.py  -> prints NIGHTCHECK lines, exit 1 on failure."""
import datetime as dt, importlib, sys, unittest
sys.path.insert(0, '.')
NAME = 'test_tv_consensus.RiskTests.test_daily_pause_disabled_allows_entry_without_resetting_losses'
bad = 0
for h, m in [(0, 0), (0, 30), (1, 59), (2, 1), (13, 0), (23, 59)]:
    fixed = dt.datetime(2026, 11, 8, h, m, tzinfo=dt.timezone.utc)
    import tv_consensus_scalper as tv
    tv.utcnow = lambda f=fixed: f
    import test_tv_consensus as T
    importlib.reload(T); T.tv.utcnow = lambda f=fixed: f
    r = unittest.TextTestRunner(verbosity=0, stream=open('/dev/null', 'w')).run(unittest.TestLoader().loadTestsFromName(NAME))
    ok = r.wasSuccessful(); bad += not ok
    print(f"NIGHTCHECK {h:02d}:{m:02d} {'OK' if ok else 'FAIL'}")
sys.exit(1 if bad else 0)
