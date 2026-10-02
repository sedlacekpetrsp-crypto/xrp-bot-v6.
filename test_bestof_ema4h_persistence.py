import asyncio,json,unittest
from unittest.mock import patch
from datetime import datetime,timezone
import bestof_bot as bot

class Cursor:
 def __init__(self,db):self.db=db
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def execute(self,query,params=None):
  if 'INSERT INTO bestof_state' in query:self.db['state']=json.loads(params[0])
  if 'INSERT INTO bestof_trades' in query:self.db['trades'].insert(0,tuple(params[:13])+tuple(datetime.fromisoformat(s) for s in params[13:]))
 def fetchone(self):return (self.db['state'],)
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

if __name__=='__main__':unittest.main()
