import unittest
from elite.impulse_v42 import signals

class ImpulseTests(unittest.TestCase):
    def sample(self, name):
        b=[(i,100,101,99,100) for i in range(60)]
        b += [(60,100,110,100,110) if name=='v42' else (60,110,110,100,100)]
        b += [(i,106,108,105,107) for i in range(61,64)]
        b += [(64,107,110,106,109)]
        return b

    def test_waits_for_three_complete_stabilization_hours(self):
        for name in ('v42','v43'):
            b=self.sample(name);s=signals(b,name)
            self.assertTrue(all(s[i].stop_distance==0 for i in range(60,64)))
            self.assertGreater(s[64].stop_distance,0)
            self.assertEqual(s[64].target_distance,2*s[64].stop_distance)
            self.assertEqual(s[64].max_bars,864)

    def test_invalidation_and_expiry(self):
        for name in ('v42','v43'):
            b=self.sample(name);b[62]=(62,106,108,99,107)
            self.assertEqual(signals(b,name)[64].stop_distance,0)
            b=self.sample(name)[:61]+[(i,106,108,105,107) for i in range(61,73)]
            b += [(73,107,110,106,109)]
            self.assertEqual(signals(b,name)[73].stop_distance,0)

    def test_not_same_bar_and_not_unstable_range(self):
        b=self.sample('v42');b[62]=(62,106,111,105,107)
        self.assertEqual(signals(b,'v42')[64].stop_distance,0)

    def test_future_cannot_change_signal_and_event_consumed(self):
        for name in ('v42','v43'):
            b=self.sample(name);s=signals(b,name)
            extended=b+[(65,109,200,108,199),(66,199,202,198,201)]
            full=signals(extended,name)
            self.assertEqual(s,{k:v for k,v in full.items() if k<len(b)})
            self.assertEqual(full[65].stop_distance,0)
