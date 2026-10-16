import unittest
from elite.episode_v51 import gate
from elite.research_engine import Decision

class EpisodeTests(unittest.TestCase):
    def test_only_initial_hour_then_reset(self):
        raw={11:Decision(3),23:Decision(3),35:Decision(),47:Decision(4)}
        out=gate(raw,raw)
        self.assertEqual([i for i,d in out.items() if d.stop_distance>0],[11,47])

    def test_btc_recovery_does_not_rearm_existing_xrp_episode(self):
        raw={11:Decision(3),23:Decision(3)}
        base={11:Decision(),23:Decision(3)}
        self.assertFalse(any(d.stop_distance for d in gate(base,raw).values()))

    def test_exits_targets_and_time_preserved(self):
        raw={11:Decision(3),23:Decision(3)}
        base={11:Decision(3,7,False,10),23:Decision(3,7,True,10)}
        d=gate(base,raw)[23]
        self.assertEqual(d,Decision(0,7,True,10))

    def test_prefix_and_clock_check(self):
        raw={11:Decision(3),23:Decision(3),35:Decision(),47:Decision(3)}
        self.assertEqual(gate({11:raw[11],23:raw[23]},{11:raw[11],23:raw[23]}),
                         {i:d for i,d in gate(raw,raw).items() if i<=23})
        with self.assertRaises(ValueError):gate({11:Decision()},{23:Decision()})
