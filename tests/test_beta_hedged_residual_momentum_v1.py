import unittest
from dataclasses import replace
from math import exp

from research.beta_hedged_residual_momentum_v1 import (Config, DAY_MS, HOUR_MS, SYMBOLS,
                                                        backtest, pair_signal)

def daily_sample(days=80):
    config=Config(beta_days=20,residual_days=5,residual_threshold=0.03,hold_hours=24,
                  cooldown_hours=24,leg_stop=0.30,fee=0,slippage=0,annual_borrow=0)
    daily={s:[] for s in SYMBOLS}; prices={s:100.0 for s in SYMBOLS}
    for d in range(days):
        btc_r=0.01 if d%2==0 else -0.006
        returns={'BTCUSDT':btc_r,'ETHUSDT':1.1*btc_r,
                 'SOLUSDT':1.2*btc_r+(0.01 if d>=days-5 else 0),
                 'XRPUSDT':0.8*btc_r}
        for s in SYMBOLS:
            opened=prices[s]; prices[s]*=exp(returns[s])
            daily[s].append({'timestamp':d*DAY_MS,'open':opened,'high':max(opened,prices[s]),
                             'low':min(opened,prices[s]),'close':prices[s]})
    return daily,config

def hourly_from_daily(daily):
    market={s:[] for s in SYMBOLS}
    for s in SYMBOLS:
        for d,day in enumerate(daily[s]):
            start=day['open']; end=day['close']
            for h in range(24):
                opened=start+(end-start)*h/24; close=start+(end-start)*(h+1)/24
                market[s].append({'timestamp':d*DAY_MS+h*HOUR_MS,'open':opened,
                                  'high':max(opened,close),'low':min(opened,close),
                                  'close':close,'volume':1.0})
    return market

class BetaResidualTests(unittest.TestCase):
    def test_signal_selects_positive_sol_residual(self):
        daily,config=daily_sample()
        setup=pair_signal(daily,79,config)
        self.assertIsNotNone(setup)
        self.assertEqual(setup[1], 'SOLUSDT')
        self.assertEqual(setup[2], 'ALT_LONG')

    def test_entry_uses_next_day_open_and_no_overlap(self):
        daily,config=daily_sample(90); market=hourly_from_daily(daily)
        result=backtest(market,0,90*DAY_MS,config)
        self.assertTrue(result['trades'])
        self.assertTrue(all(t['entry_ts']%DAY_MS==0 for t in result['trades']))
        for a,b in zip(result['trades'],result['trades'][1:]):
            self.assertGreaterEqual(b['entry_ts'],a['exit_ts']+config.cooldown_hours*HOUR_MS)

    def test_gap_stop_and_short_borrow(self):
        daily,config=daily_sample(90); market=hourly_from_daily(daily)
        baseline=backtest(market,0,90*DAY_MS,config)
        entry=baseline['trades'][0]['entry_ts']//HOUR_MS; alt=baseline['trades'][0]['alt']
        market[alt][entry+1]['open']*=0.5
        market[alt][entry+1]['low']=min(market[alt][entry+1]['low'],market[alt][entry+1]['open'])
        market[alt][entry+1]['high']=max(market[alt][entry+1]['high'],market[alt][entry+1]['open'])
        result=backtest(market,0,90*DAY_MS,replace(config,leg_stop=0.10,annual_borrow=0.08))
        self.assertEqual(result['trades'][0]['reason'],'GAP_STOP')
        self.assertGreater(result['trades'][0]['borrow_cost'],0)

    def test_higher_costs_reduce_equity(self):
        daily,config=daily_sample(90); market=hourly_from_daily(daily)
        low=backtest(market,0,90*DAY_MS,replace(config,fee=0.0001,slippage=0.0001,annual_borrow=0.04))
        high=backtest(market,0,90*DAY_MS,replace(config,fee=0.001,slippage=0.001,annual_borrow=0.16))
        self.assertLess(high['ending_equity'],low['ending_equity'])

if __name__=='__main__': unittest.main()
