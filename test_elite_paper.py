import copy
import unittest
from unittest.mock import patch
import elite_paper as e


def rows(n,step,start=0):
    return [[start+i*step,100.,101.,99.,100.] for i in range(n)]


def snapshot(now):
    return {'provider':'binance','price':100.,
            'V18':rows(210,3600000,now//3600000*3600000-210*3600000),
            'BTC':rows(210,3600000,now//3600000*3600000-210*3600000),
            'V56':rows(210,14400000,now//14400000*14400000-210*14400000),
            '5m':rows(720,300000,now//300000*300000-720*300000)}


class PaperTest(unittest.TestCase):
    now=3600000*300

    def open(self,family='V18'):
        s=e.initial(); d=snapshot(self.now)
        with patch.object(e,'signal',return_value=(10.,False,86400000)):
            s,events=e.advance(s,family,d,self.now)
            self.assertEqual(events,[])  # Never backfill a pre-start signal.
            now=self.now+14400000
            s,events=e.advance(s,family,snapshot(now),now)
        self.assertEqual(len(events),1)
        return s,now

    def test_accounting_and_stop(self):
        s,now=self.open()
        p=s['position']; before=copy.deepcopy(s)
        self.assertAlmostEqual(p['qty']*(p['entry']*1.001-p['stop']*.9996*.999),50.)
        d=snapshot(now+20000); d['price']=p['stop']
        with patch.object(e,'signal',return_value=(10.,False,0)):
            s,events=e.advance(s,'V18',d,now+20000)
        self.assertAlmostEqual(s['cash'],9950.)
        self.assertAlmostEqual(events[0]['pnl'],-50.)
        self.assertEqual(s['trades'],1)
        self.assertIsNotNone(before['position'])  # Input never mutated.
        self.assertIsNone(s['position'])
        self.assertAlmostEqual(s['cash']-10000,s['realized_pnl'])

    def test_idempotent_restart_and_no_reentry(self):
        s,now=self.open(); restored=copy.deepcopy(s)
        with patch.object(e,'signal',return_value=(10.,False,0)):
            s,events=e.advance(restored,'V18',snapshot(now),now)
            self.assertEqual(s,restored); self.assertEqual(events,[])
            s,events=e.advance(s,'V18',snapshot(now+20000),now+20000)
            self.assertEqual(events,[])

    def test_provider_change_fails_closed(self):
        s,now=self.open(); d=snapshot(now+20000); d['provider']='kraken'
        with self.assertRaisesRegex(ValueError,'Provider'): e.advance(s,'V18',d,now+20000)

    def test_expired_entry_not_backfilled(self):
        s=e.initial(); d=snapshot(self.now)
        with patch.object(e,'signal',return_value=(10.,False,0)):
            s,_=e.advance(s,'V18',d,self.now)
            s,events=e.advance(s,'V18',snapshot(self.now+3700000),self.now+3700000)
        self.assertEqual(events,[])

    def test_gap_stop_and_no_signal_reentry(self):
        s,now=self.open(); d=snapshot(now+3600000); d['price']=80.
        with patch.object(e,'signal',return_value=(10.,False,0)):
            s,events=e.advance(s,'V18',d,now+3600000)
        self.assertEqual(len(events),1); self.assertLess(events[0]['pnl'],-50.)
        self.assertIsNone(s['position'])

    def test_stop_low_after_entry_and_exclude_preentry(self):
        s,now=self.open(); s['position']['entered_at']=now+1000
        d=snapshot(now+300000); d['5m'][-1][3]=1.
        with patch.object(e,'signal',return_value=(0.,False,0)):
            s,events=e.advance(s,'V18',d,now+300000)
            self.assertEqual(events,[])  # low could precede entry
            d=snapshot(now+600000); d['5m'][-1][3]=1.
            s,events=e.advance(s,'V18',d,now+600000)
        self.assertEqual(events[0]['reason'],'STOP_OBSERVED')

    def test_v56_history_survives_rolling_window(self):
        s,now=self.open('V56'); n=len(s['history']); first=s['history'][0]
        with patch.object(e,'signal',return_value=(0.,False,0)):
            s,_=e.advance(s,'V56',snapshot(now+14400000),now+14400000)
        self.assertEqual(len(s['history']),n+1); self.assertEqual(s['history'][0],first)

    def test_candle_validation(self):
        raw=rows(3,3600000)
        self.assertEqual(len(e.candles(raw,3600000,9000000)),2)
        self.assertEqual(len(e.candles(raw,3600000,7200000)),1)
        self.assertEqual(len(e.candles(raw,3600000,7230000)),2)
        with self.assertRaises(ValueError): e.candles(raw,3600000,18000000)
        raw[1][0]+=1
        with self.assertRaises(ValueError): e.candles(raw,3600000,9000000)

    def test_history_gap_rejected(self):
        with self.assertRaises(ValueError): e.append_history(rows(10,14400000),rows(10,14400000,20*14400000),14400000)

    def test_flat_signals(self):
        x=rows(240,3600000)
        self.assertEqual(e.signal('V18',x,x),(0,False,0))
        self.assertEqual(e.signal('V56',x),(0,False,14*86400000))


if __name__=='__main__': unittest.main()
