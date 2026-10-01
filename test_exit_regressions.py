"""Isolated behavioral checks; no network, database, or profitability assumptions."""
import ast
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
import unittest


def functions(path, names, env):
    tree=ast.parse(Path(path).read_text())
    tree.body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    exec(compile(tree,path,'exec'),env)
    return env


class ExitTests(unittest.TestCase):
    def test_fly_holds_valid_old_trade_and_confirms_failure(self):
        now=datetime.now(timezone.utc)
        p=dict(symbol='XRP',side='LONG',entry_price=100,risk_distance=2,stop_loss=98,take_profit=104,
               opened_at=(now-timedelta(hours=2)).isoformat())
        price=[99.4]; closed=[]; cache={'XRP':{'ts':1}}
        sample=dict(z3=-1,book=.4,spread=.0001)
        async def live(*a,**k):return price[0]
        async def monitor(*a):return sample
        m=SimpleNamespace(paper_position=p,get_live_price=live,utcnow=lambda:now,save_state=lambda:None)
        env=dict(m=m,datetime=datetime,monitor=monitor,_monitor_cache=cache,
                 BREAKEVEN_TRIGGER_R=.9,PROFIT_MODE_R=1.15,PROFIT_MIN_LOCK_R=.2,
                 PROFIT_GIVEBACK_R=.5,DANGER_MAX_MR=.45,Z_DANGER=.55,
                 close_trade=lambda price,reason:closed.append(reason))
        f=functions('v8_fly_layer.py',{'manage_position'},env)['manage_position']
        for _ in range(5):asyncio.run(f())
        self.assertEqual(closed,[]) # repeated cached data is only one confirmation
        sample.update(z3=1,book=.6);cache['XRP']['ts']=2;asyncio.run(f())
        self.assertEqual(p['exit_confirmations'],0)
        for stamp in (3,4,5):
            sample.update(z3=-1,book=.4);cache['XRP']['ts']=stamp;asyncio.run(f())
        self.assertEqual(closed,['CONFIRMED SETUP FAILURE'])
        closed.clear();price[0]=97;asyncio.run(f())
        self.assertEqual(closed,['STOP LOSS'])

    def test_leadlag_time_alone_holds_then_distinct_candles_exit(self):
        now=datetime.now(timezone.utc);closed=[];price=[99.5]
        p=dict(side='LONG',entry=100,stop=98,tp=104,risk_dollars=2,peak_net=0,
               opened_at=(now-timedelta(hours=1)).isoformat())
        async def live(*a,**k):return price[0]
        env=dict(state={'open_position':p,'balance':10000},base=SimpleNamespace(get_live_price=live),
                 TRADE_SYMBOL='XRP',net_pnl_for_exit=lambda p,x:(0,0,0,-.5),
                 BREAKEVEN_TRIGGER_R=.9,PROFIT_LOCK_TRIGGER_R=1.25,PROFIT_GIVEBACK_R=.5,
                 save_state=lambda:None,close_trade=lambda price,reason:closed.append(reason),
                 utcnow=lambda:now,datetime=datetime,EXIT_LAG_RETURN=.0007,
                 BOOK_FLIP_LONG=.48,BOOK_FLIP_SHORT=.52)
        f=functions('lead_lag_scalper.py',{'manage_position'},env)['manage_position']
        a=dict(candle_time=1,lag_return=.002,leader_return=.002,book_imbalance=.6)
        asyncio.run(f(a));self.assertEqual(closed,[])
        a.update(candle_time=2,leader_return=-.001,book_imbalance=.4)
        for _ in range(4):asyncio.run(f(a))
        self.assertEqual(closed,[])
        a['candle_time']=3;asyncio.run(f(a))
        self.assertEqual(closed,['CONFIRMED LEADER REVERSAL'])
        closed.clear();price[0]=97;asyncio.run(f(a))
        self.assertEqual(closed,['STOP LOSS'])

    def test_whale_cooldown_does_not_block_another_symbol(self):
        now=datetime.now(timezone.utc)
        env=dict(state={'open_positions':[dict(symbol='BTCUSDT',side='LONG',opened_at=now.isoformat())]},
                 utcnow=lambda:now,datetime=datetime,SYMBOL='BTCUSDT',SAME_SIDE_COOLDOWN_MINUTES=30)
        f=functions('app_blue_whale_mirror.py',{'_same_side_too_soon'},env)['_same_side_too_soon']
        self.assertTrue(f('LONG','BTCUSDT'));self.assertFalse(f('LONG','ETHUSDT'))

    def test_fly_install_enables_pullbacks(self):
        tree=ast.parse(Path('v8_fly_layer.py').read_text())
        install=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='install')
        value=next(n.value for n in ast.walk(install) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='ENABLED_SETUPS' for t in n.targets))
        self.assertIn('TREND_PULLBACK',ast.literal_eval(value))

if __name__=='__main__':unittest.main()
