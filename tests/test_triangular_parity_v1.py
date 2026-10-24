import unittest
from research.triangular_parity_v1 import BAR_MS,Config,backtest,dislocations,execute_cycle,with_cost_stress


def sample(count=30,dislocation=.01):
    bars=[]
    for i in range(count):
        btc=100; cross=.05; eth=btc*cross*(1+dislocation if i%3==0 else 1)
        bars.append({'timestamp':i*BAR_MS,'btcusdt_open':btc,'btcusdt_close':btc,'ethusdt_open':eth,'ethusdt_close':eth,
                     'ethbtc_open':cross,'ethbtc_close':cross})
    return bars


class TriangularParityTests(unittest.TestCase):
    def test_both_route_dislocations(self):
        forward,reverse=dislocations(sample(1)[0]); self.assertAlmostEqual(forward,.01); self.assertLess(reverse,0)
        bar=sample(1,-.01)[0]; self.assertGreater(dislocations(bar)[1],0)
    def test_signal_executes_next_bar_and_cooldown(self):
        result=backtest(sample(),0,30*BAR_MS,Config(fee_rate=0,slippage_rate=0,cooldown_bars=4))
        self.assertEqual(result['trades'][0]['execution_ts'],BAR_MS)
        for a,b in zip(result['trades'],result['trades'][1:]): self.assertGreaterEqual(b['execution_ts'],a['execution_ts']+4*BAR_MS)
    def test_adverse_gap_is_realized_not_signal_close(self):
        bars=sample(3); bars[1].update({'ethusdt_open':4.9,'ethusdt_close':4.9})
        trade=backtest(bars,0,3*BAR_MS,Config(fee_rate=0,slippage_rate=0))['trades'][0]
        self.assertLess(trade['net_pnl'],0); self.assertLess(trade['execution_dislocation'],0)
    def test_three_leg_fees_reduce_cycle(self):
        bar=sample(1)[0]; gross=execute_cycle(bar,'USDT_BTC_ETH_USDT',100,Config(fee_rate=0,slippage_rate=0))
        net=execute_cycle(bar,'USDT_BTC_ETH_USDT',100,Config())
        self.assertLess(net,gross)
    def test_stress_reduces_equity(self):
        data=sample(); base=Config()
        self.assertLess(backtest(data,0,30*BAR_MS,with_cost_stress(base))['ending_equity'],backtest(data,0,30*BAR_MS,base)['ending_equity'])


if __name__=='__main__': unittest.main()
