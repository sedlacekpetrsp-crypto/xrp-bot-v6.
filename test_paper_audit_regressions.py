"""Settlement, stale-exit and journal regressions; no profitability claims."""
import asyncio
import copy
import math
import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from test_exit_regressions import functions
import app_blue_whale_mirror as whale


class StaleTests(unittest.TestCase):
    def run_case(self, side):
        now=datetime.now(timezone.utc)
        opposite='SHORT' if side=='LONG' else 'LONG'
        position=dict(side=side,entry=100,qty=1,stop=98 if side=='LONG' else 102,
                      tp=104 if side=='LONG' else 96,risk_dollars=2,peak_net=0,
                      opened_at=(now-timedelta(hours=2)).isoformat(),stale_confirmations=1)
        closed=[]
        env=dict(state={'open_position':position,'balance':10000},math=math,
                 base=SimpleNamespace(get_live_price=AsyncMock(return_value=99 if side=='LONG' else 101)),
                 SYMBOL='XRP',utcnow=lambda:now,datetime=datetime,
                 net_pnl_for_exit=lambda p,x:(0,0,0,-1),close_trade=lambda p,r:closed.append(r),
                 save_state=lambda:None,heartbeat_state=lambda:None,
                 BREAK_EVEN_TRIGGER_R=.9,MIN_LOCKED_NET_R=.1,TRAIL_TRIGGER_R=1.4,
                 TRAIL_GIVEBACK_R=.75,FLIP_EXIT_MIN_AGE=5,STALE_HOLD_MINUTES=75,MIN_SCORE_EDGE=42)
        manage=functions('tv_consensus_scalper.py',{'manage_position'},env)['manage_position']
        a=dict(candle_time=100,trend_15m='NEUTRAL',long_score=10 if side=='LONG' else 90,
               short_score=90 if side=='LONG' else 10)
        for _ in range(5):asyncio.run(manage(a))
        self.assertEqual(closed,[])
        self.assertEqual(position['stale_confirmations'],1)
        for stamp in (None,99):
            asyncio.run(manage(dict(a,candle_time=stamp)))
        self.assertEqual(closed,[])
        asyncio.run(manage(dict(a,candle_time=101,trend_15m=side)))
        self.assertEqual(position['stale_confirmations'],0)
        asyncio.run(manage(dict(a,candle_time=102)))
        # Persistence/restart retains the last candle and count.
        env['state']['open_position']=copy.deepcopy(position)
        asyncio.run(manage(dict(a,candle_time=102)))
        self.assertEqual(closed,[])
        asyncio.run(manage(dict(a,candle_time=103)))
        self.assertEqual(closed,['TV STALE TRADE'])
    def test_long(self):self.run_case('LONG')
    def test_short(self):self.run_case('SHORT')


class FlySettlementTests(unittest.TestCase):
    def module(self, database=False):
        now=datetime.now(timezone.utc)
        p=dict(symbol='XRPUSDC',side='LONG',setup='BREAKOUT',entry_price=100,qty=1,
               opened_at=(now-timedelta(minutes=1)).isoformat(),initial_risk_usdc=2)
        return SimpleNamespace(paper_position=p,SLIPPAGE_RATE=.0002,FEE_RATE=.00095,
            RISK_PER_TRADE=.001,utcnow=lambda:now,timedelta=timedelta,
            PAPER_BALANCE=10000,trade_history=[],DATABASE_URL='mock' if database else None,
            last_entry_candle={},save_state=lambda:None,daily_risk_status=lambda:(0,0,0,0),
            MAX_CONSECUTIVE_LOSSES=4,LOSS_STREAK_COOLDOWN_MIN=30)
    def test_double_close_and_restart_do_not_debit_twice(self):
        m=self.module(); original=copy.deepcopy(m.paper_position)
        close=functions('v8_fly_layer.py',{'close_trade'},{'m':m,'datetime':datetime})['close_trade']
        close(99,'STOP');balance=m.PAPER_BALANCE
        close(99,'STOP');m.paper_position=original;close(99,'STOP')
        self.assertEqual(m.PAPER_BALANCE,balance)
        self.assertEqual(len(m.trade_history),1)
        self.assertIsNone(m.paper_position)
    def test_failed_transaction_keeps_position_and_balance_for_retry(self):
        m=self.module(True);original=copy.deepcopy(m.paper_position)
        class Cursor:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def execute(self,sql,args=None):
                if 'INSERT INTO v8fixed_trades' in sql:raise RuntimeError('write failure')
                self.query=sql
            def fetchone(self):return ('key',) if 'fly_settlements' in self.query else None
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def cursor(self):return Cursor()
            def commit(self):raise AssertionError('must not commit')
        m.get_db=lambda:Connection()
        close=functions('v8_fly_layer.py',{'close_trade'},{'m':m,'datetime':datetime})['close_trade']
        with self.assertRaisesRegex(RuntimeError,'write failure'):close(99,'STOP')
        self.assertEqual(m.paper_position,original)
        self.assertEqual(m.PAPER_BALANCE,10000)
        self.assertEqual(m.trade_history,[])

    def test_database_settlement_and_persisted_duplicate(self):
        for duplicate in (False,True):
            m=self.module(True);calls=[]
            class Cursor:
                def __enter__(self):return self
                def __exit__(self,*a):return False
                def execute(self,sql,args=None):
                    self.query=sql;calls.append((sql,args))
                def fetchone(self):
                    if 'SELECT 1' in self.query:return (1,) if duplicate else None
                    return ('key',)
            class Connection:
                def __enter__(self):return self
                def __exit__(self,*a):return False
                def cursor(self):return Cursor()
                def commit(self):calls.append(('COMMIT',None))
            m.get_db=lambda:Connection()
            close=functions('v8_fly_layer.py',{'close_trade'},{'m':m,'datetime':datetime})['close_trade']
            close(99,'STOP');close(99,'STOP')
            writes=[sql for sql,args in calls if 'INSERT INTO v8fixed_trades' in sql]
            self.assertEqual(len(writes),0 if duplicate else 1)
            self.assertEqual(len(m.trade_history),0 if duplicate else 1)
            self.assertIsNone(m.paper_position)
            if duplicate:self.assertEqual(m.PAPER_BALANCE,10000)
            else:
                self.assertAlmostEqual(m.PAPER_BALANCE,10000+m.trade_history[0]['pnl'])
                self.assertEqual(calls[-1][0],'COMMIT')


class JournalTests(unittest.TestCase):
    def test_bounded_history_survives_payload_and_does_not_mutate_account(self):
        state=copy.deepcopy(whale.state)
        state.update(signal_journal=[],market_prices={'XRPUSDT':1.5})
        with patch.object(whale,'state',state):
            check=dict(symbol='XRPUSDT',strategy='FIB_618_786',reason='MTF rejected',
                       candidate_key='swing',candidate_entry=1.5,candidate_stop=1.48,candidate_target=1.54)
            for _ in range(510):whale.record_signal_checks([check])
            self.assertEqual(len(state['signal_journal']),500)
            self.assertEqual(whale._persistent_payload()['signal_journal'],state['signal_journal'])
            self.assertEqual(state['balance'],whale.START_BALANCE)
            self.assertEqual(state['signal_journal'][-1]['candidate_key'],'swing')
            whale.record_signal_checks([dict(check,error=True)])
            self.assertNotIn('observed_price',state['signal_journal'][-1])

if __name__=='__main__':unittest.main()
