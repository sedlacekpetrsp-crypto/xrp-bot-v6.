import unittest
from strategy import backtest, evaluate, validate


def row(start=0, p=.7, end_price=100):
    return dict(window_start=start,window_end=start+300,signal_ts=start+60,
                poly_ts=start+59,binance_ts=start+59,entry_ts=start+61,
                exit_ts=start+300,p_up=p,past_price=99,signal_price=100,
                entry_price=100,exit_price=end_price)


class Tests(unittest.TestCase):
    def test_round_trip_costs(self):
        r=backtest([row()],.6,10,5)
        self.assertLess(r['net_return'],0)
        self.assertAlmostEqual(r['net_return'],.9995*.999/(1.0005*1.001)-1)
        self.assertAlmostEqual(r['max_closed_trade_drawdown'],-r['net_return'])

    def test_future_signal_rejected(self):
        r=row(); r['poly_ts']=62
        with self.assertRaises(ValueError): validate([r])

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError): validate([row(),row()])

    def test_settlement_rejected(self):
        with self.assertRaises(ValueError): validate([row(p=1)])

    def test_no_signal_no_trades(self):
        self.assertEqual(backtest([row(p=.51)],.6,10,5)['trade_count'],0)

    def test_holdout_does_not_select_threshold(self):
        train=[row(0,p=.57,end_price=110),row(300,p=.7,end_price=101)]
        a=evaluate(train+[row(900,end_price=150)],900)
        b=evaluate(train+[row(900,end_price=50)],900)
        self.assertEqual(a['threshold'],b['threshold'])
        self.assertEqual(a['test_rows'],1)

    def test_missing_data_is_incomplete(self):
        self.assertEqual(evaluate([],900)['verdict'],'TEST NEDOKONČEN')


if __name__ == '__main__': unittest.main()
