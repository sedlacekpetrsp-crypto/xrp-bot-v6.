import asyncio,json,unittest
from unittest.mock import patch
from datetime import datetime,timezone
import bestof_bot as bot

class Cursor:
 def __init__(self,db):self.db=db
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def execute(self,query,params=None):
  self.last=None
  if 'INSERT INTO bestof_state' in query:self.db['state']=json.loads(params[0])
  if 'INSERT INTO bestof_trades' in query:self.db['trades'].insert(0,tuple(params[:13])+tuple(datetime.fromisoformat(s) for s in params[13:]))
  if 'pg_advisory_xact_lock' in query:self.db.setdefault('locks',[]).append(tuple(params))
  if 'SELECT id FROM bestof_trades' in query:
   sym,setup,opened=params;opened=datetime.fromisoformat(opened)
   hit=[r for r in self.db['trades'] if r[0]==sym and r[2]==setup and r[13]==opened]
   self.last=('dedupe',(1,) if hit else None)
 def fetchone(self):
  if getattr(self,'last',None) and self.last[0]=='dedupe':return self.last[1]
  return (self.db['state'],)
 def fetchall(self):return self.db['trades']
class Connection:
 def __init__(self,db):self.db=db
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def cursor(self):return Cursor(self.db)
 def commit(self):pass

class Persistence(unittest.TestCase):
 def test_actual_core_save_restore_mixed_positions_and_ema_trade(self):
  c=bot.core;db={'state':{},'trades':[]};now=datetime(2026,10,2,20,0,30,tzinfo=timezone.utc)
  legacy=dict(symbol='SOLUSDT',setup='BREAKOUT',side='SHORT',qty=1,entry_price=120,risk_usdt=10,stop_loss=121,take_profit=118,opened_at=now.isoformat())
  with patch.multiple(c,DATABASE_URL='test',get_db=lambda:Connection(db),utcnow=lambda:now,positions={'SOLUSDT':legacy.copy()},PAPER_BALANCE=10000.,last_entry_candle={},cooldown_until={},trade_history=[]):
   a=dict(signal='LONG',setup=bot.ema4h.SETUP,candle_time=int(now.timestamp()*1000)-30000,price_closed=100.,atr=1.)
   self.assertTrue(bot.ema4h.open_ema(c,'XRPUSDT',a,100))
   original=dict(c.positions['XRPUSDT']);dedup=dict(c.last_entry_candle)
   c.positions={};c.last_entry_candle={};c.load_state()
   self.assertEqual(c.positions['XRPUSDT'],original);self.assertEqual(c.positions['SOLUSDT'],legacy)
   self.assertEqual(c.last_entry_candle,dedup)
   bot.ema4h.close_ema(c,'XRPUSDT',105,'EMA 4h CROSS DOWN');balance=c.PAPER_BALANCE
   c.trade_history=[];c.load_state()
   self.assertEqual(c.trade_history[0]['setup'],'EMA_4H');self.assertAlmostEqual(c.PAPER_BALANCE,balance)
   self.assertEqual(bot.ema4h.summary(c)['groups'][1]['trades'],1)
   self.assertEqual(c.positions['SOLUSDT'],legacy)

 def test_second_close_of_same_opening_is_not_saved(self):
  # 2026-11-05 09:14 UTC: dvě instance při zero-downtime deployi uzavřely stejnou pozici
  c=bot.core;db={'state':{},'trades':[]}
  t=dict(symbol='XRPUSDT',side='LONG',setup='BREAKOUT',entry_market=1.3227,entry_price=1.32296454,exit_market=1.3151,exit_price=1.31483698,qty=1091.9,gross_pnl=-8.3,slippage=0.58,fees=1.44,pnl=-10.31,reason='STOP LOSS',opened_at='2026-11-05T08:20:29.773893+00:00',closed_at='2026-11-05T09:14:07.761682+00:00')
  with patch.multiple(c,DATABASE_URL='test',get_db=lambda:Connection(db)):
   self.assertTrue(c.save_trade(dict(t)))
   self.assertFalse(c.save_trade(dict(t,closed_at='2026-11-05T09:14:10.872418+00:00')))
   self.assertEqual(len(db['trades']),1)
   other=dict(t,opened_at='2026-11-05T10:20:00+00:00',closed_at='2026-11-05T11:00:00+00:00')
   self.assertTrue(c.save_trade(other));self.assertEqual(len(db['trades']),2)
   self.assertTrue(all(l==c.TRADE_WRITE_LOCK for l in db['locks']))

if __name__=='__main__':unittest.main()
