import unittest
from elite.double_bottom_v52 import hourly_signals


def fixture():
    bars = [(12*k+11, 103., 104., 102., 103.) for k in range(40)]
    bars[16] = (203, 101., 103., 100., 102.)
    bars[24] = (299, 101., 103., 100., 102.)
    bars[27] = (335, 103., 106., 102., 105.)
    return bars


class DoubleBottomTests(unittest.TestCase):
    def test_confirmed_pattern_enters_once(self):
        out = hourly_signals(fixture())
        self.assertEqual([i for i, d in out.items() if d.stop_distance], [335])
        d = out[335]
        self.assertEqual(d.target_distance, 2*d.stop_distance)
        self.assertEqual(d.max_bars, 864)

    def test_future_bars_never_rewrite_signals(self):
        bars = fixture(); full = hourly_signals(bars)
        for n in range(17, len(bars)):
            self.assertEqual(hourly_signals(bars[:n]), {k:v for k,v in full.items() if k<=bars[n-1][0]})

    def test_breakout_before_confirmation_not_traded_retroactively(self):
        bars = fixture()
        for k in range(25,40): bars[k] = (12*k+11, 105., 107., 102., 106.)
        self.assertFalse(any(d.stop_distance for d in hourly_signals(bars).values()))

    def test_floor_breach_invalidates_pattern(self):
        bars = fixture(); bars[27] = (335, 103., 106., 95., 105.)
        self.assertFalse(any(d.stop_distance for d in hourly_signals(bars).values()))

    def test_distant_or_unequal_pivots_rejected(self):
        bars = fixture(); bars[24] = (299, 99., 103., 96., 102.)
        self.assertFalse(any(d.stop_distance for d in hourly_signals(bars).values()))
