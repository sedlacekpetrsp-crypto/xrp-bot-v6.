import copy
import json
import unittest
from unittest.mock import patch
import swing_paper as s

NOW=1800000000000
F='aroon_1h_4h'

def quote(price=100,now=NOW): return {'XRPUSDT':{'price':price,'time':now}}
def frame(side=1,now=NOW): return {'XRPUSDT':dict(candle=now,close=100,atr=1,side=side,exit_long=False,exit_short=False)}
def ready():
 st=s.initial();st['activated_at']=NOW-3600000;return st

def opened(side=1): return s.advance(ready(),F,quote(),frame(side),NOW)[0]

class Paper(unittest.TestCase):
 def test_snapshot_initial_and_running(self):
  with patch.object(s,"runtime",{}):
   data=s.snapshot();self.assertEqual(len(data["accounts"]),2)
   self.assertTrue(all(a["mode"]=="PAPER" for a in data["accounts"]))
   st=opened();s.runtime[F]={"state":st,"quotes":quote(),"checks":frame(),"errors":{},"persistence":"postgres"}
   json.dumps(s.snapshot(),allow_nan=False)
 def test_independent_accounts(self):
  a=s.initial();b=s.initial();a['positions']['X']=1;self.assertEqual(b['positions'],{})
 def test_boot_does_not_enter_old_signal(self):
  st,_=s.advance(s.initial(),F,quote(),frame(now=NOW-1000),NOW)
  self.assertFalse(st['positions'])
 def test_long_stop_costs_target_risk(self):
  st=opened();p=st['positions']['XRPUSDT'];loss=s.net(p,p['stop_loss'],NOW)[0]
  self.assertAlmostEqual(loss,-50);self.assertLessEqual(p['qty']*p['entry_price'],3500)
 def test_short_stop_and_carry(self):
  st=opened(-1);p=st['positions']['XRPUSDT']
  self.assertAlmostEqual(s.net(p,p['stop_loss'],NOW)[0],-50)
  self.assertGreater(s.net(p,90,NOW)[0],0)
  self.assertLess(s.net(p,90,NOW+28800000)[0],s.net(p,90,NOW)[0])
 def test_stale_quote_does_not_trade(self):
  st,_=s.advance(ready(),F,quote(now=NOW-16000),frame(),NOW);self.assertFalse(st['positions'])
 def test_old_signal_does_not_trade(self):
  st,_=s.advance(ready(),F,quote(),frame(now=NOW-130000),NOW);self.assertFalse(st['positions'])
 def test_close_without_indicator_data(self):
  st=opened();after,trades=s.advance(st,F,quote(90),{},NOW+1000)
  self.assertFalse(after['positions']);self.assertEqual(len(trades),1)
  self.assertAlmostEqual(after['balance'],10000+trades[0]['pnl'])
 def test_restart_dedup_and_cooldown(self):
  st=opened();st=json.loads(json.dumps(st));st,trades=s.advance(st,F,quote(90),frame(),NOW+1000)
  again,ts=s.advance(st,F,quote(),frame(),NOW+2000)
  self.assertFalse(again['positions']);self.assertFalse(ts);self.assertEqual(again['count'],1)
 def test_signal_exit(self):
  st=opened();d=frame(now=NOW+3600000);d['XRPUSDT']['exit_long']=True
  result,trades=s.advance(st,F,quote(110,NOW+3600000),d,NOW+3600000)
  self.assertEqual(len(trades),1);self.assertIn('AROON',trades[0]['reason']);self.assertGreater(trades[0]['pnl'],0)
 def test_trail_never_loosens(self):
  st=opened();d=frame(now=NOW+3600000);d['XRPUSDT'].update(close=110,atr=1,side=0)
  st,_=s.advance(st,F,quote(110,NOW+3600000),d,NOW+3600000);stop=st['positions']['XRPUSDT']['stop_loss']
  d['XRPUSDT'].update(candle=NOW+7200000,close=108,atr=4)
  st,_=s.advance(st,F,quote(108,NOW+7200000),d,NOW+7200000)
  self.assertEqual(st['positions']['XRPUSDT']['stop_loss'],stop)
 def test_two_positions_and_priority(self):
  q={sym:{'price':100,'time':NOW} for sym in s.SYMBOLS};d={sym:frame()['XRPUSDT'] for sym in s.SYMBOLS}
  st,_=s.advance(ready(),F,q,d,NOW)
  self.assertEqual(list(st['positions']),['XRPUSDT','BTCUSDT'])
 def test_notional_cap(self):
  d=frame();d['XRPUSDT']['atr']=.1
  st,_=s.advance(ready(),F,quote(),d,NOW);p=st['positions']['XRPUSDT']
  self.assertAlmostEqual(p['qty']*p['entry_price'],3500)
 def test_atomic_close_rollback_and_retry(self):
  db={'state':opened(),'trades':[]};fail=[True]
  class Conn:
   def __enter__(self):self.temp=copy.deepcopy(db);return self
   def __exit__(self,t,v,tb):
    if t is None:db.update(self.temp)
   def execute(self,sql,args):
    if sql.startswith('SELECT'):
     self.row=(self.temp['state'],);return self
    if sql.startswith('INSERT'):
     self.temp['trades'].append(json.loads(args[2]))
    if sql.startswith('UPDATE'):
     if fail[0]:raise RuntimeError('simulated commit failure')
     self.temp['state']=json.loads(args[0])
    return self
   def fetchone(self):return self.row
  with patch.object(s,'connect',lambda url:Conn()):
   with self.assertRaises(RuntimeError):s.commit_tick('db',F,quote(90),{},NOW+1000)
   self.assertTrue(db['state']['positions']);self.assertFalse(db['trades'])
   fail[0]=False
   result=s.commit_tick('db',F,quote(90),{},NOW+1000)
   result=s.commit_tick('db',F,quote(90),{},NOW+1000)
   self.assertEqual(len(db['trades']),1);self.assertEqual(result['count'],1)

if __name__=='__main__':unittest.main()
