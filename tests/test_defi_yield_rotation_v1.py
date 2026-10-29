import unittest
from dataclasses import replace
from research.defi_yield_rotation_v1 import Config, DAY, backtest, make_yield_signals


def prices(n=50, start=0, price=100.0):
    return [dict(timestamp=start+i*DAY, open=price, high=price+1, low=price-1, close=price) for i in range(n)]


class DefiYieldRotationTests(unittest.TestCase):
    def test_signal_is_prefix_invariant_and_uses_fixed_window(self):
        rows=[]
        for i in range(40):
            rows.append(dict(timestamp=i*DAY+12_000, apy=5.0 if i < 33 else 4.0))
        full=make_yield_signals(rows)
        prefix=make_yield_signals(rows[:36])
        self.assertEqual(prefix, [x for x in full if x["source_timestamp"] <= rows[35]["timestamp"]])
        self.assertTrue(any(x["change_7_pp"] == -1.0 for x in full))

    def test_source_must_precede_entry(self):
        rows=prices()
        rows[20]["yield_signal"] = dict(source_timestamp=rows[20]["timestamp"], apy=2, median_30=3, change_7_pp=-1)
        trades,_=backtest(rows,0,100*DAY)
        self.assertEqual(trades,[])

    def test_next_open_costs_sizing_and_no_overlap(self):
        rows=prices(60)
        sig=dict(source_timestamp=20*DAY-1, apy=2, median_30=3, change_7_pp=-1)
        rows[20]["yield_signal"]=sig
        rows[21]["yield_signal"]=dict(sig,source_timestamp=21*DAY-1)
        rows[31]["yield_signal"]=dict(sig,source_timestamp=31*DAY-1)
        trades,_=backtest(rows,0,100*DAY)
        self.assertEqual(len(trades),2)
        self.assertAlmostEqual(trades[0]["entry"],100.02)
        self.assertLessEqual(trades[0]["leg_notional"],2000.000001)
        self.assertGreater(trades[0]["fees"],0)
        self.assertGreater(trades[1]["entry_timestamp"],trades[0]["exit_timestamp"])

    def test_ambiguous_bar_stop_wins(self):
        rows=prices(40)
        rows[20]["yield_signal"]=dict(source_timestamp=20*DAY-1,apy=2,median_30=3,change_7_pp=-1)
        rows[20].update(high=110,low=90)
        trades,_=backtest(rows,0,100*DAY)
        self.assertEqual(trades[0]["reason"],"STOP")

    def test_gap_stop_uses_worse_open(self):
        rows=prices(40)
        rows[20]["yield_signal"]=dict(source_timestamp=20*DAY-1,apy=2,median_30=3,change_7_pp=-1)
        rows[21].update(open=90,high=91,low=89,close=90)
        trades,_=backtest(rows,0,100*DAY)
        self.assertEqual(trades[0]["reason"],"GAP_STOP")
        self.assertEqual(trades[0]["raw_exit"],90)

    def test_double_cost_is_worse_for_same_path(self):
        rows=prices(40)
        rows[20]["yield_signal"]=dict(source_timestamp=20*DAY-1,apy=2,median_30=3,change_7_pp=-1)
        base,_=backtest(rows,0,100*DAY)
        stress,_=backtest(rows,0,100*DAY,replace(Config(),fee=.0019,slippage=.0004))
        self.assertLess(stress[0]["pnl"],base[0]["pnl"])

    def test_price_gap_blocks_atr_warmup(self):
        rows=prices(40)
        del rows[15]
        rows[20-1]["yield_signal"]=dict(source_timestamp=20*DAY-1,apy=2,median_30=3,change_7_pp=-1)
        trades,_=backtest(rows,0,100*DAY)
        self.assertEqual(trades,[])


if __name__ == "__main__":
    unittest.main()
