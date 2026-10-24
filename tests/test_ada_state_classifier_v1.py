import unittest
from research.ada_state_classifier_v1 import BAR_MS,HOUR_MS,Config,backtest,feature_at,resample_4h,with_cost_stress


def hourly(hours=200):
    bars=[]; price=100.0
    for i in range(hours):
        opened=price; price*=1.001 if i%16<8 else 0.9995
        bars.append({'timestamp':i*HOUR_MS,'open':opened,'high':max(opened,price)*1.002,'low':min(opened,price)*0.998,
                     'close':price,'quote_volume':1000+i})
    return bars


class StateClassifierTests(unittest.TestCase):
    def test_resample_requires_complete_four_hours(self):
        data=hourly(12); self.assertEqual(len(resample_4h(data)),3)
        self.assertEqual(len(resample_4h([b for b in data if b['timestamp']!=5*HOUR_MS])),2)
    def test_feature_does_not_change_when_future_changes(self):
        bars=resample_4h(hourly()); before=feature_at(bars,35).copy(); bars[36]['close']*=2
        self.assertTrue((before==feature_at(bars,35)).all())
    def test_score_enters_next_bar_and_no_overlap(self):
        bars=resample_4h(hourly(300)); scores={bars[35]['timestamp']:0.9,bars[36]['timestamp']:0.9,bars[50]['timestamp']:0.1}
        result=backtest(bars,scores,0,10**15,Config(stop_loss=.5,take_profit=.5,maximum_hold_bars=2,fee_rate=0,slippage_rate=0))
        self.assertEqual(result['trades'][0]['entry_ts'],bars[36]['timestamp'])
        for a,b in zip(result['trades'],result['trades'][1:]): self.assertGreaterEqual(b['entry_ts'],a['exit_ts']+2*BAR_MS)
    def test_short_gap_stop_uses_worse_open(self):
        bars=resample_4h(hourly(300)); scores={bars[35]['timestamp']:0.1}; bars[37]['open']=bars[36]['open']*2; bars[37]['high']=bars[37]['open']; bars[37]['low']=min(bars[37]['low'],bars[37]['open'])
        trade=backtest(bars,scores,0,10**15,Config(fee_rate=0,slippage_rate=0))['trades'][0]
        self.assertEqual(trade['reason'],'GAP_STOP'); self.assertEqual(trade['exit'],bars[37]['open'])
    def test_cost_stress_reduces_equity(self):
        bars=resample_4h(hourly(300)); scores={bars[i]['timestamp']:(.9 if i%2 else .1) for i in range(35,len(bars))}; base=Config(stop_loss=.5,take_profit=.5)
        self.assertLess(backtest(bars,scores,0,10**15,with_cost_stress(base))['ending_equity'],backtest(bars,scores,0,10**15,base)['ending_equity'])


if __name__=='__main__': unittest.main()
