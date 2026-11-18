"""Executes the real dashboard formatter (#69) in Node: Prague DST, ambiguous hour, missing values.

Skipped when Node.js is not installed. Extracts fmtDate/duration from PAGE verbatim,
so the test covers the shipped JavaScript, not a Python re-implementation.
"""
import json
import shutil
import subprocess
import unittest

from research.max_effect_forward_bot import PAGE

NODE = shutil.which("node")


def _run(calls):
    src = PAGE[PAGE.index("const fmtDate"):PAGE.index("function px")]
    prog = src + "\nconsole.log(JSON.stringify([" + ",".join(calls) + "]));"
    out = subprocess.run([NODE, "-e", prog], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "node not installed")
class DashboardFormatterJsTests(unittest.TestCase):
    def test_missing_and_invalid(self):
        self.assertEqual(_run(["fmtDate(null)", "fmtDate('')", "fmtDate('x')"]), ["neuvedeno"] * 3)

    def test_winter_summer_and_zone_label(self):
        winter, summer = _run(["fmtDate('2026-01-15T12:00:00+00:00')",
                               "fmtDate('2026-07-15T12:00:00+00:00')"])
        self.assertIn("13:00", winter)
        self.assertIn("14:00", summer)
        self.assertNotEqual(winter.split()[-1], summer.split()[-1])  # CET vs CEST label differs

    def test_ambiguous_autumn_hour_is_distinguishable(self):
        a, b = _run(["fmtDate('2026-10-25T00:30:00+00:00')", "fmtDate('2026-10-25T01:30:00+00:00')"])
        self.assertIn("02:30", a)
        self.assertIn("02:30", b)
        self.assertNotEqual(a, b)

    def test_python_isoformat_microseconds(self):
        (v,) = _run(["fmtDate('2026-11-16T00:12:09.862000+00:00')"])
        self.assertIn("01:12", v)

    def test_duration(self):
        self.assertEqual(_run([
            "duration('2026-03-28T23:00:00+00:00','2026-03-29T23:00:00+00:00')",
            "duration('2026-11-16T00:05:00+00:00',null)",
            "duration('2026-11-17T00:00:00+00:00','2026-11-16T00:00:00+00:00')"]),
            ["1 d 0 h 0 min", "neuvedeno", "neuvedeno"])


if __name__ == "__main__":
    unittest.main()
