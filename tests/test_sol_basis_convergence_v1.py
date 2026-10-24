import unittest
from research.sol_basis_convergence_v1 import Config, HOUR_MS, backtest, premium, with_cost_stress


def sample(hours=120, basis=0.006):
    bars=[]
    for i in range(hours):
        spot=100+i*0.01; current=basis if i<30 else 0.0
        bars.append({"timestamp":i*HOUR_MS,"spot_open":spot,"spot_close":spot,
                     "perp_open":spot*(1+current),"perp_close":spot*(1+current)})
    return bars


class BasisTests(unittest.TestCase):
    def test_premium_formula(self): self.assertAlmostEqual(premium(sample(1)[0]),0.006)
    def test_entry_uses_previous_close_and_target_next_open(self):
        result=backtest(sample(),{},0,120*HOUR_MS,Config(spot_fee_rate=0,futures_fee_rate=0,slippage_rate=0))
        self.assertEqual(result["trades"][0]["entry_ts"],HOUR_MS)
        self.assertEqual(result["trades"][0]["exit_ts"],31*HOUR_MS)
        self.assertEqual(result["trades"][0]["reason"],"TARGET")
    def test_gap_stop_fills_at_worse_synchronized_open(self):
        data=sample(); data[10]["perp_close"]=data[10]["spot_close"]*1.02; data[11]["perp_open"]=data[11]["spot_open"]*1.03
        result=backtest(data,{},0,120*HOUR_MS,Config(spot_fee_rate=0,futures_fee_rate=0,slippage_rate=0))
        self.assertEqual(result["trades"][0]["reason"],"GAP_STOP"); self.assertGreater(result["trades"][0]["exit_premium"],0.012)
    def test_short_perp_receives_positive_funding(self):
        result=backtest(sample(),{8*HOUR_MS:0.001},0,120*HOUR_MS,Config(spot_fee_rate=0,futures_fee_rate=0,slippage_rate=0))
        self.assertGreater(result["trades"][0]["funding_pnl"],0)
    def test_stress_reduces_equity(self):
        funding={8*HOUR_MS:0.001}; base=Config()
        self.assertLess(backtest(sample(),funding,0,120*HOUR_MS,with_cost_stress(base))["ending_equity"],
                        backtest(sample(),funding,0,120*HOUR_MS,base)["ending_equity"])


if __name__ == "__main__": unittest.main()
