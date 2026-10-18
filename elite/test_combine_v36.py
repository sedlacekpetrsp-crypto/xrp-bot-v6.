import unittest
from elite.research_engine import Decision
from elite.combine_v36 import combine,prepare

class CombinationTests(unittest.TestCase):
    def test_truth_table_one_size_and_unchanged_exit(self):
        for a in (0,3):
            for b in (0,3):
                for n in ('v36','v37'):
                    d=combine(Decision(a,exit=True),Decision(b,exit=True),n)
                    expected=(a>0 or b>0) if n=='v36' else (a>0 and b>0)
                    self.assertEqual(d.stop_distance,3 if expected else 0)
                    self.assertTrue(d.exit)
                    self.assertEqual(d.target_distance,0)
    def test_incompatible_signals_fail_closed(self):
        for b in (Decision(3,exit=True),Decision(4),Decision(3,1),Decision(3,max_bars=2)):
            with self.assertRaises(ValueError):combine(Decision(3),b,'v36')
    def test_unknown_fails(self):
        with self.assertRaises(ValueError):combine(Decision(),Decision(),'v99')
    def test_future_cannot_change_past(self):
        r=[(i*300000,100+i*.01,101+i*.01,99+i*.01,100+i*.01) for i in range(3100)]
        f=[(x[0],10,6) for x in r];cut=3001
        changed=r[:cut]+[(t,o*2,h*2,l*2,c*2) for t,o,h,l,c in r[cut:]]
        changedf=f[:cut]+[(t,100,90) for t,v,b in f[cut:]]
        expected,_=prepare(r[:cut],r[:cut],f[:cut]);actual,_=prepare(changed,changed,changedf)
        for n in expected:self.assertEqual(expected[n],{i:s for i,s in actual[n].items() if i<cut})
