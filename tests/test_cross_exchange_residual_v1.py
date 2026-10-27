import unittest
from dataclasses import replace
from research.cross_exchange_residual_v1 import Config, STEP, adverse_residual, backtest, residual


def bar(t, r=0.0, move=0.0):
    bx=1.0; cx=(1+r)*(1+move); cb=100.0; bb=100.0
    return {"timestamp":t,"cxrp_open":cx,"cxrp_high":cx*1.001,"cxrp_low":cx*.999,"cxrp_close":cx,"bxrp_open":bx,"bxrp_high":bx*1.001,"bxrp_low":bx*.999,"bxrp_close":bx,"cbtc_open":cb,"cbtc_high":cb*1.001,"cbtc_low":cb*.999,"cbtc_close":cb,"bbtc_open":bb,"bbtc_high":bb*1.001,"bbtc_low":bb*.999,"bbtc_close":bb}


class TestCrossExchange(unittest.TestCase):
    def test_btc_basis_removed(self):
        b=bar(0,-.01); b["cbtc_close"]=101; self.assertAlmostEqual(residual(b),-.0198019802)
    def test_adverse_is_lower(self):
        b=bar(0,-.01); self.assertLess(adverse_residual(b),residual(b))
    def test_next_open_and_nonoverlap(self):
        bars=[bar(i*STEP, r) for i,r in enumerate([-.01,-.008,0,0,-.01,-.008,0,0])]
        c=replace(Config(),coinbase_fee=0,binance_fee=0,coinbase_slippage=0,binance_slippage=0)
        tr,_=backtest(bars,[],0,8*STEP,c); self.assertEqual([x["entry_timestamp"] for x in tr],[STEP,5*STEP])
    def test_costs_hurt(self):
        bars=[bar(i*STEP,r) for i,r in enumerate([-.01,-.008,0,0])]
        free=replace(Config(),coinbase_fee=0,binance_fee=0,coinbase_slippage=0,binance_slippage=0)
        a,_=backtest(bars,[],0,4*STEP,free); b,_=backtest(bars,[],0,4*STEP,Config()); self.assertLess(b[0]["pnl"],a[0]["pnl"])
    def test_gap_stop_worse_open(self):
        bars=[bar(0,-.01),bar(STEP,-.02),bar(2*STEP,0)]
        tr,_=backtest(bars,[],0,3*STEP,Config()); self.assertEqual(tr[0]["reason"],"GAP_STOP")
    def test_prefix_invariance(self):
        bars=[bar(i*STEP,r) for i,r in enumerate([-.01,-.008,0,0,.1])]
        a,_=backtest(bars[:4],[],0,4*STEP,Config()); b,_=backtest(bars,[],0,4*STEP,Config()); self.assertEqual(a,b)

if __name__=="__main__": unittest.main()
