import unittest,tempfile,zipfile,hashlib
from pathlib import Path
from elite.volume_v26 import load_volume,align_volume
from elite.candidates_v26 import signal,decisions

class VolumeTests(unittest.TestCase):
    def test_read_base_volume_and_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'XRPUSDT-5m-2025-01.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('data.csv','1735689600000000,100,101,99,100,12.5,0,9999\n')
            manifest=[dict(month='2025-01',bars=1,sha256=hashlib.sha256(p.read_bytes()).hexdigest())]
            rows=[(1735689600000,100.,101.,99.,100.)]
            self.assertEqual(load_volume(d,rows,manifest),[(1735689600000,12.5)])
            p.write_bytes(p.read_bytes()+b'corrupted')
            with self.assertRaises(ValueError):load_volume(d,rows,manifest)
    def test_invalid_values_and_alignment(self):
        for v in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):align_volume([(0,1,1,1,1)],[(0,v)])
        with self.assertRaises(ValueError):align_volume([(0,1,1,1,1)],[(300000,1)])
        with self.assertRaises(ValueError):align_volume([(0,1,1,1,1)],[])
    def test_breakout_volume_gate_and_control(self):
        b=[(i,100,101,99,100) for i in range(201)];b[-1]=(200,100,103,99,102)
        v=[10]*201
        self.assertEqual(signal(b,v,200,'v26').stop_distance,0)
        self.assertGreater(signal(b,v,200,'v26',False).stop_distance,0)
        v[-1]=20
        self.assertGreater(signal(b,v,200,'v26').stop_distance,0)
    def test_rejection_requires_price_confirmation(self):
        b=[(i,100,101,99,100) for i in range(201)];b[-1]=(200,100,102,95,101)
        v=[10]*200+[20]
        self.assertGreater(signal(b,v,200,'v27').stop_distance,0)
        b[-1]=(200,100,102,95,99)
        self.assertEqual(signal(b,v,200,'v27').stop_distance,0)
    def test_complete_volume_bars_and_no_future(self):
        r=[(i*300000,100,101,99,100) for i in range(10000)]
        v=[(row[0],1.) for row in r];cut=9901
        changed=v[:cut]+[(t,999999.) for t,_ in v[cut:]]
        for n in ('v26','v27'):
            self.assertEqual(decisions(r[:cut],v[:cut],n),{i:s for i,s in decisions(r,changed,n).items() if i<cut})
