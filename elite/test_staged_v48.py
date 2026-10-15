import unittest,math
from elite.staged_v48 import Setup,prepare

class StagedTests(unittest.TestCase):
    def test_three_distinct_hours_and_consumption(self):
        s=Setup()
        self.assertEqual(s.step(0,101,100,1,.4,True).stop_distance,0)
        self.assertEqual(s.step(1,99,100,1,.1,True).stop_distance,0)
        self.assertEqual(s.step(2,101,100,1,.1,True).stop_distance,3)
        self.assertEqual(s.step(3,101,100,1,.1,True).stop_distance,0)
        self.assertEqual(s.counts['entries'],1)

    def test_expiry_invalidation_and_cost_failure(self):
        for invalid in (True,False):
            s=Setup();s.step(0,101,100,1,.4,True);s.step(1,99,100,1,.1,True)
            d=s.step(2 if invalid else 49,101,100,1,.1,not invalid)
            self.assertEqual(d.stop_distance,0)
        s=Setup();s.step(0,101,100,1,.4,True);s.step(1,99,100,1,.1,True)
        self.assertEqual(s.step(2,101,100,.1,.1,True).stop_distance,0)
        self.assertEqual(s.step(3,101,100,1,.1,True).stop_distance,0)
        self.assertEqual(s.counts['confirmed'],1)
        self.assertEqual(s.counts['entries'],0)

    def test_boundary48_allowed_and_no_entry_without_pullback(self):
        s=Setup();s.step(0,101,100,1,.4,True)
        self.assertEqual(s.step(46,102,100,1,.1,True).stop_distance,0)
        s.step(47,99,100,1,.1,True)
        self.assertGreater(s.step(48,101,100,1,.1,True).stop_distance,0)

    def test_prefix_replay(self):
        rows=[]
        for i in range(250*12):
            p=100+i/1000+2*math.sin(i/90)
            rows.append((i*300000,p,p+1,p-1,p))
        full,_=prepare(rows);part,_=prepare(rows[:230*12+3])
        self.assertEqual(part,{i:d for i,d in full.items() if i<230*12+3})
