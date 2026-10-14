import unittest,tempfile,zipfile,hashlib
from pathlib import Path
from elite.turnover_v34 import load_turnover,align_turnover
from elite.candidates_v34 import weekly_vwap,decisions,signal,DAY

class VWAPTests(unittest.TestCase):
    def test_quote_column_and_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'XRPUSDT-5m-2025-01.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('data.csv','1735689600000000,100,101,99,100,10,0,1000,5,7.5,750,0\n')
            m=[dict(month='2025-01',bars=1,sha256=hashlib.sha256(p.read_bytes()).hexdigest())]
            rows=[(1735689600000,100.,101.,99.,100.)]
            self.assertEqual(load_turnover(d,rows,m),[(1735689600000,10.,1000.)])
            with self.assertRaises(ValueError):align_turnover(rows,[(1735689600000,10,2000)])
    def test_volume_weighting_week_reset_and_partial_week(self):
        monday=4*DAY
        r=[(monday-300000,100,100,100,100),(monday,100,100,100,100),(monday+300000,110,110,110,110),(monday+7*DAY,120,120,120,120)]
        q=[(r[0][0],10,1000),(r[1][0],1,100),(r[2][0],9,990),(r[3][0],1,120)]
        self.assertEqual(weekly_vwap(r,q),[None,100,109,120])
    def test_zero_volume_no_vwap(self):
        self.assertEqual(weekly_vwap([(4*DAY,100,100,100,100)],[(4*DAY,0,0)]),[None])
    def test_reclaim_trigger_and_week_eligibility(self):
        b=[(i,100+i*.1,101+i*.1,99+i*.1,100+i*.1) for i in range(201)]
        self.assertGreater(signal(b,200,'v34',119.9,120,True).stop_distance,0)
        self.assertEqual(signal(b,200,'v34',119.9,120,False).stop_distance,0)
    def test_reversal_trigger(self):
        b=[(i,100,101,99,100) for i in range(201)]
        b[199]=(199,94,95,92,94);b[200]=(200,94,98,93,97)
        self.assertGreater(signal(b,200,'v35',105,105,True).stop_distance,0)
        self.assertTrue(signal(b,200,'v35',96,105,True).exit)
    def test_future_quote_and_price_cannot_change_past(self):
        r=[(i*300000,100,101,99,100) for i in range(3100)];q=[(x[0],10,1000) for x in r];cut=3001
        changed=r[:cut]+[(t,200,202,198,200) for t,*_ in r[cut:]]
        cq=q[:cut]+[(t,10,2000) for t,*_ in q[cut:]]
        for n in ('v34','v35'):
            self.assertEqual(decisions(r[:cut],q[:cut],n),{i:s for i,s in decisions(changed,cq,n).items() if i<cut})
