import unittest
from elite.climax_v55 import signals


def fixture():
    b=[(48*k+47,100.,101.,99.,100.) for k in range(40)]
    b[20]=(1007,100.,101.,94.,95.)
    b[21]=(1055,95.,100.,94.,99.)
    t=[(100.,10000.)]*40
    t[20]=(300.,29000.);t[21]=(100.,9800.)
    return b,t


class ClimaxTests(unittest.TestCase):
    def test_recovery_only_after_anchor_and_once(self):
        b,t=fixture();out=signals(b,t)
        self.assertEqual([i for i,d in out.items() if d.stop_distance],[1055])
        self.assertEqual(out[1055].target_distance,2*out[1055].stop_distance)
        self.assertEqual(out[1055].max_bars,2016)

    def test_low_volume_does_not_anchor(self):
        b,t=fixture();t[20]=(100.,9666.67)
        self.assertFalse(any(d.stop_distance for d in signals(b,t).values()))

    def test_stop_breach_precedes_reclaim(self):
        b,t=fixture();b[21]=(1055,95.,100.,90.,99.)
        self.assertFalse(any(d.stop_distance for d in signals(b,t).values()))

    def test_expired_recovery_rejected(self):
        b,t=fixture()
        for k in range(21,28):
            b[k]=(48*k+47,95.,96.,94.,95.);t[k]=(100.,9500.)
        self.assertFalse(any(d.stop_distance for d in signals(b,t).values()))

    def test_prefix_causality(self):
        b,t=fixture();full=signals(b,t)
        for n in (21,22,25,39):
            self.assertEqual(signals(b[:n],t[:n]),{i:d for i,d in full.items() if i<=b[n-1][0]})

    def test_zero_volume_no_event(self):
        b,t=fixture()
        self.assertFalse(any(d.stop_distance for d in signals(b,[(0.,0.)]*len(b)).values()))
