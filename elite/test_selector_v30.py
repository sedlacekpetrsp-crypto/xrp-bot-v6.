import unittest
from datetime import datetime,timezone
from elite.selector_v30 import select,MonthlyRouter,schedule,NAMES,DAY
from elite.research_engine import Decision

class SelectorTests(unittest.TestCase):
    def scores(self):
        return {n:{str(d):dict(trades=5,net_pnl=-10,profit_factor=.8,close_mtm_drawdown_pct=5) for d in (90,180)} for n in NAMES}
    def test_cash_and_stricter_confirmation(self):
        s=self.scores();self.assertIsNone(select(s,'v30'))
        s['v5']['180'].update(net_pnl=100,profit_factor=1.5)
        self.assertEqual(select(s,'v30'),'v5');self.assertIsNone(select(s,'v31'))
        s['v5']['90']['net_pnl']=1
        self.assertEqual(select(s,'v31'),'v5')
        s['v5']['180']['trades']=4
        self.assertIsNone(select(s,'v30'))
    def test_fixed_tie_priority(self):
        s=self.scores()
        for n in ('v5','v8'):s[n]['180'].update(net_pnl=100,profit_factor=1.5)
        self.assertEqual(select(s,'v30'),'v5')
    def test_month_boundary_and_exit_owner(self):
        r=MonthlyRouter({'v5':{9:Decision(3)},'v8':{9:Decision(exit=True)}},[10],['v5'])
        self.assertEqual(r.for_position(8).stop_distance,0)
        self.assertEqual(r.for_position(9).source,'v5')
        self.assertTrue(r.for_position(9,'v8').exit)
        r=MonthlyRouter(r.streams,[10],[None])
        self.assertEqual(r.for_position(9).stop_distance,0)
        self.assertTrue(r.for_position(9,'v8').exit)
    def test_training_excludes_selected_month_and_future(self):
        ts=int(datetime(2023,4,1,tzinfo=timezone.utc).timestamp()*1000)
        rows=[(ts+i*DAY,100,101,99,100) for i in range(220)]
        calls=[]
        def scorer(rows,stream,start,end,**kwargs):
            calls.append((start,end,kwargs))
            self.assertLess(rows[end-1][0],rows[end][0])
            return dict(trades=6,net_pnl=rows[end-1][4],profit_factor=1.5,close_mtm_drawdown_pct=1)
        streams={n:{} for n in NAMES}
        starts,recs=schedule(rows,streams,scorer)
        self.assertTrue(starts)
        self.assertEqual(recs[0]['training_end_timestamp'],rows[starts[0]-1][0])
        altered=rows[:starts[0]]+[(t,o,h,l,999) for t,o,h,l,c in rows[starts[0]:]]
        _,changed=schedule(altered,streams,scorer)
        self.assertEqual(recs[0],changed[0])
        self.assertTrue(all(k['fee']==.002 for _,_,k in calls))
