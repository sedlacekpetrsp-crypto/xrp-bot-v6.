"""Regression checks for MAX-efekt PAPER dashboard trade timestamps (#69)."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from research.max_effect_forward import fresh, step, DAY_MS
from research.max_effect_forward_bot import PAGE

class MaxEffectTimestampTests(unittest.TestCase):
    def test_dashboard_fields(self):
        for field in ("fmtDate(x.entry_at)", "fmtDate(t.entry_at)",
                      "fmtDate(t.exit_at)", "duration(t.entry_at,t.exit_at)",
                      "Europe/Prague", "Čistý P/L", "neuvedeno"):
            self.assertIn(field, PAGE)

    def test_dst_timezone_reference(self):
        zone = ZoneInfo("Europe/Prague")
        winter = datetime.fromisoformat("2026-01-15T12:00:00+00:00").astimezone(zone)
        summer = datetime.fromisoformat("2026-07-15T12:00:00+00:00").astimezone(zone)
        self.assertEqual(winter.hour, 13)
        self.assertEqual(summer.hour, 14)

    def test_fresh_ledger_has_empty_history(self):
        ledger = fresh()
        self.assertEqual(ledger["trades"], [])
        self.assertEqual(ledger["positions"], {})

if __name__ == "__main__":
    unittest.main()
