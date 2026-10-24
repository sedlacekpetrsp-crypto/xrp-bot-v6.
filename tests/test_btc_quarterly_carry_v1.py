import unittest
from research.btc_quarterly_carry_v1 import Config, DAY_MS, HOUR_MS, annualized_basis, backtest_contract, with_cost_stress


def sample(days=35, raw_basis=0.015):
    expiry=days*DAY_MS+8*HOUR_MS; bars=[]
    for i in range(days*24+9):
        ts=i*HOUR_MS; spot=100+i*0.001; remaining=max(0,(expiry-ts)/DAY_MS); basis=raw_basis*remaining/days
        bars.append({"timestamp":ts,"spot_open":spot,"spot_close":spot,
                     "future_open":spot*(1+basis),"future_close":spot*(1+basis)})
    return bars,expiry


class QuarterlyCarryTests(unittest.TestCase):
    def test_annualization_uses_time_remaining(self):
        bars,expiry=sample(); self.assertAlmostEqual(annualized_basis(bars[24*7],expiry),0.015*365/35,places=4)
    def test_signal_enters_next_hour_and_exits_at_expiry(self):
        bars,expiry=sample(); result=backtest_contract(bars,expiry,Config(spot_fee_rate=0,futures_fee_rate=0,slippage_rate=0))
        self.assertIsNotNone(result["trade"]); self.assertEqual(result["trade"]["reason"],"EXPIRY")
        self.assertEqual(result["trade"]["entry_ts"]%DAY_MS,HOUR_MS)
    def test_missing_transition_prevents_entry(self):
        bars,expiry=sample(); bars=[b for b in bars if b["timestamp"]!=8*DAY_MS]
        result=backtest_contract(bars,expiry,Config(entry_window_days=28,entry_cutoff_days=27))
        self.assertIsNone(result["trade"])
    def test_spread_stop_fills_next_open(self):
        bars,expiry=sample(); config=Config(stop_annualized_basis=0.20,spot_fee_rate=0,futures_fee_rate=0,slippage_rate=0)
        for b in bars:
            if b["timestamp"]==9*DAY_MS: b["future_close"]=b["spot_close"]*1.05
            if b["timestamp"]==9*DAY_MS+HOUR_MS: b["future_open"]=b["spot_open"]*1.06
        trade=backtest_contract(bars,expiry,config)["trade"]
        self.assertEqual(trade["reason"],"GAP_STOP"); self.assertEqual(trade["exit_ts"],9*DAY_MS+HOUR_MS)
    def test_stress_reduces_equity(self):
        bars,expiry=sample(); base=Config()
        self.assertLess(backtest_contract(bars,expiry,with_cost_stress(base))["ending_equity"],backtest_contract(bars,expiry,base)["ending_equity"])


if __name__ == "__main__": unittest.main()
