import unittest
from dataclasses import replace
from unittest.mock import patch
from research.residual_snapback_v1 import Config,STEP,backtest,signal,validate

class ResidualTests(unittest.TestCase):
    def markets(self,n=220):
        m={s:[] for s in ('XRPUSDT','BTCUSDT','ETHUSDT')}
        for s in m:
            for i in range(n):
                p=100*(1.0001**i);m[s].append(dict(timestamp=i*STEP,open=p,high=p*1.002,low=p*.998,close=p))
        return m
    def run_one(self,m=None,c=Config()):
        m=m or self.markets()
        with patch('research.residual_snapback_v1.signal',side_effect=lambda m,i,c:dict(atr=1.,beta=1.,zscore=-3.) if i==170 else None):
            return backtest(m,0,220*STEP,c)
    def test_next_open_and_time_exit(self):
        t=self.run_one()[0];self.assertEqual((t['signal_index'],t['entry_index'],t['exit_index']),(170,171,182));self.assertEqual(t['reason'],'TIME')
    def test_costs_stress_and_sizing(self):
        t=self.run_one()[0];s=self.run_one(c=replace(Config(),fee=.0019,slippage=.0004))[0]
        self.assertAlmostEqual(t['gross']-t['fees']-t['slippage_cost'],t['pnl']);self.assertLess(s['pnl'],t['pnl'])
        self.assertLessEqual(t['entry']*t['qty'],2000.000001);self.assertLessEqual((t['entry']-t['stop'])*t['qty'],50.000001)
    def test_stop_first_and_gap(self):
        m=self.markets();m['XRPUSDT'][171].update(high=110.,low=90.)
        self.assertEqual(self.run_one(m)[0]['reason'],'STOP')
        m=self.markets();m['XRPUSDT'][172].update(open=90.,high=91.,low=89.,close=90.)
        self.assertEqual(self.run_one(m)[0]['reason'],'GAP_STOP')
    def test_signal_is_causal(self):
        m=self.markets()
        for i in range(2,170):m['XRPUSDT'][i]['close']*=1+(i%3-1)*1e-5
        m['XRPUSDT'][170]['close']*=.95;m['XRPUSDT'][170]['low']*=.94
        v=signal(m,170);self.assertIsNotNone(v)
        for bars in m.values():
            for b in bars[171:]:b['close']=1e8
        self.assertEqual(signal(m,170),v)
    def test_gap_and_alignment(self):
        m=self.markets();[bars.pop(100) for bars in m.values()];validate(m);self.assertIsNone(signal(m,169))
        m=self.markets();m['BTCUSDT'].pop()
        with self.assertRaises(ValueError):validate(m)
    def test_flat_no_signal_or_trade(self):
        m=self.markets();self.assertIsNone(signal(m,170));self.assertEqual(backtest(m,0,220*STEP),[])

if __name__=='__main__':unittest.main()
