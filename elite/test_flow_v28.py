import unittest,tempfile,zipfile,hashlib
from pathlib import Path
from elite.flow_v28 import load_flow,align_flow
from elite.candidates_v28 import signal,decisions,ratio

class FlowTests(unittest.TestCase):
    def test_correct_columns_and_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'XRPUSDT-5m-2025-01.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('data.csv','1735689600000000,100,101,99,100,12.5,0,9999,5,7.5,8888,0\n')
            m=[dict(month='2025-01',bars=1,sha256=hashlib.sha256(p.read_bytes()).hexdigest())]
            rows=[(1735689600000,100.,101.,99.,100.)]
            self.assertEqual(load_flow(d,rows,m),[(1735689600000,12.5,7.5)])
            p.write_bytes(p.read_bytes()+b'x')
            with self.assertRaises(ValueError):load_flow(d,rows,m)
    def test_invalid_and_impossible_buy(self):
        for buy in (-1,11,float('nan'),float('inf')):
            with self.assertRaises(ValueError):align_flow([(0,1,1,1,1)],[(0,10,buy)])
        with self.assertRaises(ValueError):align_flow([(0,1,1,1,1)],[(1,10,5)])
        with self.assertRaises(ValueError):align_flow([(0,1,1,1,1)],[])
    def test_ratio_is_volume_weighted(self):
        self.assertAlmostEqual(ratio([(100,90),(900,90)]),.18)
        self.assertIsNone(ratio([(0,0)]))
    def test_v28_gate_and_control(self):
        b=[(i,100,101,99,100) for i in range(201)];b[-1]=(200,100,103,99,102)
        f=[(10,5)]*201
        self.assertEqual(signal(b,f,200,'v28').stop_distance,0)
        self.assertGreater(signal(b,f,200,'v28',False).stop_distance,0)
        f[-3:]=[(10,6)]*3
        self.assertGreater(signal(b,f,200,'v28').stop_distance,0)
    def test_v29_sell_majority_recovery(self):
        b=[(i,100,101,99,100) for i in range(201)];b[-1]=(200,100,102,95,101)
        f=[(10,4)]*201
        self.assertGreater(signal(b,f,200,'v29').stop_distance,0)
        f[-1]=(10,6)
        self.assertEqual(signal(b,f,200,'v29').stop_distance,0)
        f[-1]=(0,0)
        self.assertEqual(signal(b,f,200,'v29').stop_distance,0)
    def test_future_flow_invariance(self):
        r=[(i*300000,100,101,99,100) for i in range(10000)]
        f=[(x[0],10,5) for x in r];cut=9901
        changed=f[:cut]+[(t,100000,90000) for t,_,_ in f[cut:]]
        for n in ('v28','v29'):
            self.assertEqual(decisions(r[:cut],f[:cut],n),{i:s for i,s in decisions(r,changed,n).items() if i<cut})
