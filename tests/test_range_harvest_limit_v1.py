import unittest
from dataclasses import replace
from research.range_harvest_limit_v1 import Config,DAY_MS,HOUR_MS,backtest,setup

def sample(days=35):
    bars=[]; price=100.0
    for d in range(days):
        day_open=price; day_close=100.0+(1 if d%2==0 else -1)
        for h in range(24):
            opened=day_open+(day_close-day_open)*h/24; close=day_open+(day_close-day_open)*(h+1)/24
            bars.append({'timestamp':d*DAY_MS+h*HOUR_MS,'open':opened,
                         'high':max(opened,close)+0.2,'low':min(opened,close)-0.2,
                         'close':close,'volume':1.0})
        price=day_close
    return bars

class RangeHarvestTests(unittest.TestCase):
    def test_setup_uses_completed_days(self):
        from research.range_harvest_limit_v1 import daily_bars
        days=daily_bars(sample()); candidate=setup(days,10,Config(regime_days=5,maximum_efficiency=0.8))
        self.assertIsNotNone(candidate); self.assertLess(candidate['entry'],candidate['fair'])

    def test_limit_entry_is_after_setup_and_time_exit(self):
        data=sample(); config=Config(regime_days=5,maximum_efficiency=0.8,entry_atr=0.1,stop_atr=10,
                                    maximum_hold_hours=6,entry_fee=0,exit_fee=0,exit_slippage=0)
        result=backtest(data,0,len(data)*HOUR_MS,config)
        self.assertTrue(result['trades']); self.assertGreaterEqual(result['trades'][0]['entry_ts'],6*DAY_MS)
        self.assertTrue(all(t['exit_ts']-t['entry_ts']<=config.maximum_hold_hours*HOUR_MS
                            for t in result['trades']))

    def test_gap_stop_uses_worse_open(self):
        data=sample(); config=Config(regime_days=5,maximum_efficiency=0.8,entry_atr=0.1,stop_atr=0.5,
                                    entry_fee=0,exit_fee=0,exit_slippage=0)
        baseline=backtest(data,0,len(data)*HOUR_MS,config); entry=baseline['trades'][0]['entry_ts']//HOUR_MS
        data[entry+1]['open']=50; data[entry+1]['low']=50; data[entry+1]['high']=max(data[entry+1]['high'],50)
        result=backtest(data,0,len(data)*HOUR_MS,config)
        self.assertEqual(result['trades'][0]['reason'],'GAP_STOP'); self.assertEqual(result['trades'][0]['exit'],50)

    def test_taker_stress_reduces_equity(self):
        data=sample(); base=Config(regime_days=5,maximum_efficiency=0.8,entry_atr=0.1,stop_atr=10)
        from research.range_harvest_limit_v1 import with_taker_stress
        self.assertLess(backtest(data,0,len(data)*HOUR_MS,with_taker_stress(base))['ending_equity'],
                        backtest(data,0,len(data)*HOUR_MS,base)['ending_equity'])

if __name__=='__main__': unittest.main()
