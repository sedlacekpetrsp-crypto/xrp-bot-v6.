import unittest
from research.cross_market_dispersion_20261026.strategy import ASSETS,validate,backtest,percentile,Config

def markets(n=24*190):
    return {a:[dict(timestamp=i*3600000,open=100.,high=101.,low=99.,close=100.) for i in range(n)] for a in ASSETS}

class Tests(unittest.TestCase):
    def test_percentile(self): self.assertEqual(percentile([1,2,3,4,5],.5),3)
    def test_no_signal_flat(self): self.assertEqual(backtest(markets()),[])
    def test_gap_rejected(self):
        m=markets(100);m["BTCUSDT"][2]["timestamp"]+=1
        with self.assertRaises(ValueError):validate(m)
    def test_misalignment_rejected(self):
        m=markets(100)
        for row in m["BTCUSDT"]:row["timestamp"]+=3600000
        with self.assertRaises(ValueError):validate(m)
    def test_bad_ohlc_rejected(self):
        m=markets(100);m["XRPUSDT"][0]["low"]=102
        with self.assertRaises(ValueError):validate(m)
    def test_cost_stress_flat(self):self.assertEqual(backtest(markets(),Config(),True),[])

if __name__=="__main__":unittest.main()

class ExecutionTests(unittest.TestCase):
    def fixture(self):
        m=markets(121)
        m['BTCUSDT'][71].update(close=90.,low=90.)
        m['ETHUSDT'][71].update(close=110.,high=110.)
        return m

    def test_costs_and_ledger_reconcile(self):
        t=backtest(self.fixture(),Config(history_days=1))[0]
        self.assertEqual((t['entry_index'],t['exit_index']),(72,96))
        self.assertEqual((t['long'],t['short']),('BTCUSDT','ETHUSDT'))
        gross=t['qty_long']*(t['fill_long']-t['entry_long'])+t['qty_short']*(t['entry_short']-t['fill_short'])
        self.assertAlmostEqual(t['pnl'],gross-t['fees']-t['borrow'])
        self.assertAlmostEqual(t['equity'],10000+t['pnl'])
        self.assertAlmostEqual(t['borrow'],.3)
        self.assertLess(t['pnl'],0)
        self.assertGreater(t['drawdown_bound'],0)
        self.assertLess(backtest(self.fixture(),Config(history_days=1),True)[0]['pnl'],t['pnl'])

    def test_intrabar_pair_not_retroactive_open(self):
        m=self.fixture();m['BTCUSDT'][73]['low']=95.;m['ETHUSDT'][73]['high']=102.
        t=backtest(m,Config(history_days=1))[0]
        self.assertEqual(t['reason'],'STOP_BOUND')
        self.assertAlmostEqual(t['fill_short'],102*1.0002)
        self.assertAlmostEqual(t['held_days'],2/24)
        self.assertAlmostEqual(t['fill_long'],t['entry_long']*.97*.9998)

    def test_gap_exits_both_at_open(self):
        m=self.fixture();m['BTCUSDT'][73].update(open=90.,low=89.,high=101.)
        t=backtest(m,Config(history_days=1))[0]
        self.assertEqual(t['reason'],'STOP_GAP')
        self.assertAlmostEqual(t['fill_long'],90*.9998)
        self.assertAlmostEqual(t['fill_short'],100*1.0002)

    def test_signal_ignores_future_and_current_open(self):
        m=self.fixture();t=backtest(m,Config(history_days=1))[0]
        for a in ASSETS:
            m[a][100].update(open=200.,high=201.,low=199.,close=200.)
        t2=backtest(m,Config(history_days=1))[0]
        self.assertEqual(t,t2)

    def test_no_overlap(self):
        ts=backtest(self.fixture(),Config(history_days=1))
        self.assertTrue(all(a['exit_index']<=b['entry_index'] for a,b in zip(ts,ts[1:])))

    def test_empty_and_non_hour_timestamps_rejected(self):
        with self.assertRaises(ValueError):validate(markets(0))
        m=markets(100)
        for rows in m.values():
            for r in rows:r['timestamp']+=1
        with self.assertRaises(ValueError):validate(m)
