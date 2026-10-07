import unittest
import lh_whale as lh

class Tests(unittest.TestCase):
    def setup_account(self, side):
        s=lh.initial(); s['activated_at']=1
        a=dict(candle=300000,signal=side,stop=98 if side=='LONG' else 102)
        return lh.advance(s,dict(price=100,time=300010),a,300010),a

    def test_risk_and_net_target_both_directions(self):
        for side in ('LONG','SHORT'):
            s,_=self.setup_account(side); p=s['position']
            loss=-lh.net(p,p['stop_loss'])[0]
            self.assertLessEqual(loss,50.000001)
            self.assertAlmostEqual(lh.net(p,p['take_profit'])[0]/loss,2.5)

    def test_stale_and_duplicate_signals(self):
        s,a=self.setup_account('LONG')
        s=lh.advance(s,dict(price=98,time=300020),a,300020)
        self.assertEqual(s['count'],1)
        s['cooldown']=0
        self.assertIsNone(lh.advance(s,dict(price=100,time=300030),a,300030)['position'])
        a['candle']=600000
        self.assertIsNone(lh.advance(s,dict(price=100,time=580000),a,600010)['position'])

    def test_future_or_stale_statistics_rejected(self):
        oi=[dict(timestamp=300000,sumOpenInterest='100'),dict(timestamp=600000,sumOpenInterest='101')]
        top=[dict(timestamp=300000,longShortRatio='1.2'),dict(timestamp=600000,longShortRatio='0.1')]
        taker=[dict(timestamp=300000,buySellRatio='1.2'),dict(timestamp=600000,buySellRatio='0.1')]
        self.assertEqual(lh.futures_confirmation(oi,top,taker,600000,'LONG')['score'],3)
        with self.assertRaises(ValueError): lh.futures_confirmation(oi,top,taker,1200000,'LONG')

    def test_restart_dedup_and_failed_confirmation(self):
        s=lh.initial();s['activated_at']=1
        s=lh.advance(s,dict(price=100,time=300010),dict(candle=300000,signal='WAIT'),300010)
        self.assertIsNone(s['position'])
        s=lh.advance(s,dict(price=100,time=300020),dict(candle=300000,signal='LONG',stop=98),300020)
        self.assertIsNotNone(s['position'])

if __name__=='__main__': unittest.main()
