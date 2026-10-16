import unittest
from elite.imbalance_v54 import hourly_signals, decisions


def fixture():
    return [(12*k+11,100.,101.,99.,100.) for k in range(90)]


class ImbalanceTests(unittest.TestCase):
    def test_crossing_only_once_and_exit_on_selling(self):
        totals=[(100.,50.)]*30+[(100.,60.)]*30+[(100.,30.)]*30
        out=hourly_signals(fixture(),totals)
        buys=[d for d in out.values() if d.stop_distance]
        self.assertEqual(len(buys),1)
        self.assertEqual(buys[0].target_distance,2*buys[0].stop_distance)
        self.assertEqual(buys[0].max_bars,576)
        self.assertTrue(out[1079].exit)

    def test_volume_weighting_not_mean_of_ratios(self):
        totals=[(100.,50.)]*30+[(1000.,600.)]+[(100.,50.)]*59
        out=hourly_signals(fixture(),totals)
        self.assertGreater(out[371].stop_distance,0)

    def test_zero_volume_no_trigger(self):
        self.assertFalse(any(d.stop_distance for d in hourly_signals(fixture(),[(0.,0.)]*90).values()))

    def test_prefix_causality(self):
        bars=fixture(); totals=[(100.,50.)]*30+[(100.,60.)]*60
        full=hourly_signals(bars,totals)
        for n in (25,30,38,60,75):
            self.assertEqual(hourly_signals(bars[:n],totals[:n]),{i:d for i,d in full.items() if i<=bars[n-1][0]})

    def test_price_already_ran_too_far_blocks_entry(self):
        bars=fixture();bars=[(i,o,h+5,l,c+5) if k>=30 else (i,o,h,l,c) for k,(i,o,h,l,c) in enumerate(bars)]
        out=hourly_signals(bars,[(100.,50.)]*30+[(100.,60.)]*60)
        self.assertFalse(any(d.stop_distance for d in out.values()))

    def test_misaligned_raw_flow_rejected(self):
        with self.assertRaises(ValueError): decisions([(0,100,101,99,100)],[(300000,100,50)])
