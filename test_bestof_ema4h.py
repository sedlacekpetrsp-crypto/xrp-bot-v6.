import asyncio,copy,unittest,ast
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
import bestof_ema4h as e

NOW=datetime(2026,10,2,20,0,30,tzinfo=timezone.utc)
STAMP=int(datetime(2026,10,2,20,tzinfo=timezone.utc).timestamp()*1000)

def core():
    async def legacy_strategy(symbol):return {'signal':'WAIT','setup':None}
    async def legacy_manage(symbol):return 'legacy-managed'
    async def live(symbol,max_age):return 100.
    return SimpleNamespace(TRADING_MODE='PAPER',DATABASE_URL='test',SYMBOLS=['XRPUSDT','ETHUSDT'],PAPER_BALANCE=10000.,
      RISK_PER_TRADE=.0015,MAX_OPEN_POSITIONS=2,positions={},last_entry_candle={},cooldown_until={},trade_history=[],
      utcnow=lambda:NOW,save_state=lambda:None,save_trade=lambda t:None,cooldown_active=lambda s:False,
      COOLDOWN_AFTER_LOSS_MIN=20,COOLDOWN_AFTER_WIN_MIN=5,get_live_price=live,
      strategy_analysis=legacy_strategy,open_trade=lambda s,a,p:'legacy-open',manage_position=legacy_manage)
def signal():return dict(signal='LONG',setup=e.SETUP,candle_time=STAMP,price_closed=100.,atr=1.)

class EmaAddon(unittest.TestCase):
 def setUp(self):e._cache.clear();e.checks.clear();e.errors.clear()
 def test_risk_slots_and_persistence_fields(self):
  c=core();self.assertTrue(e.open_ema(c,'XRPUSDT',signal(),100))
  p=c.positions['XRPUSDT'];self.assertLessEqual(p['risk_usdt'],10.000001)
  self.assertAlmostEqual(-e.net_per_unit(p,p['stop_loss'])*p['qty'],p['risk_usdt'])
  self.assertFalse(e.open_ema(c,'XRPUSDT',signal(),100))
  self.assertEqual(c.last_entry_candle['EMA_4H:XRPUSDT'],STAMP)
  saved=copy.deepcopy(c.positions);c.positions=saved
  self.assertEqual(c.positions['XRPUSDT']['best_close'],100)
  c.positions.clear();self.assertFalse(e.open_ema(c,'XRPUSDT',signal(),100))
 def test_joint_risk_cap_and_two_slots(self):
  c=core();c.positions['ETHUSDT']=dict(risk_usdt=29,qty=1,entry_price=100)
  self.assertTrue(e.open_ema(c,'XRPUSDT',signal(),100));self.assertLessEqual(c.positions['XRPUSDT']['risk_usdt'],1.000001)
  self.assertFalse(e.open_ema(c,'ETHUSDT',signal(),100))
 def test_stale_signal_cooldown_and_live_mode_blocked(self):
  c=core();s=signal();s['candle_time']-=e.TF_MS;self.assertFalse(e.open_ema(c,'XRPUSDT',s,100))
  c.TRADING_MODE='LIVE';self.assertFalse(e.open_ema(c,'XRPUSDT',signal(),100))
  c.TRADING_MODE='PAPER';c.cooldown_active=lambda s:True;self.assertFalse(e.open_ema(c,'XRPUSDT',signal(),100))
 def test_legacy_priority_and_original_dispatch(self):
  c=core();c.strategy_analysis=AsyncMock(return_value={'signal':'LONG','setup':'BREAKOUT'})
  e.install(c)
  d={**signal(),'entry_signal':True,'exit_signal':False}
  with patch.object(e,'frame',new=AsyncMock(return_value=d)):
   self.assertEqual(asyncio.run(c.strategy_analysis('XRPUSDT'))['setup'],'BREAKOUT')
  self.assertEqual(c.open_trade('XRPUSDT',{'setup':'BREAKOUT'},100),'legacy-open')
  c.positions['XRPUSDT']={'setup':'BREAKOUT'}
  self.assertEqual(asyncio.run(c.manage_position('XRPUSDT')),'legacy-managed')
 def test_addon_error_never_blocks_legacy(self):
  c=core();e.install(c)
  with patch.object(e,'frame',new=AsyncMock(side_effect=ValueError('data unavailable'))):
   self.assertEqual(asyncio.run(c.strategy_analysis('XRPUSDT'))['signal'],'WAIT')
  self.assertIn('XRPUSDT',e.errors)
 def test_stop_works_even_if_indicator_data_unavailable(self):
  c=core();e.open_ema(c,'XRPUSDT',signal(),100);c.get_live_price=AsyncMock(return_value=97)
  with patch.object(e,'frame',new=AsyncMock(side_effect=ValueError('offline'))) as f:
   asyncio.run(e.manage_ema(c,'XRPUSDT'));f.assert_not_called()
  self.assertNotIn('XRPUSDT',c.positions);self.assertLess(c.trade_history[0]['pnl'],0)
 def test_close_fees_and_separate_stats(self):
  c=core();e.open_ema(c,'XRPUSDT',signal(),100);e.close_ema(c,'XRPUSDT',105,'TEST')
  t=c.trade_history[0];self.assertAlmostEqual(t['pnl'],t['gross_pnl']-t['slippage']-t['fees'])
  self.assertAlmostEqual(c.PAPER_BALANCE,10000+t['pnl'])
  c.trade_history.append({'setup':'BREAKOUT','pnl':-3})
  summary=e.summary(c);self.assertEqual(summary['groups'][0]['net_pnl'],-3);self.assertEqual(summary['groups'][1]['trades'],1)
 def test_trail_only_closed_bars_and_never_loosen(self):
  c=core();e.open_ema(c,'XRPUSDT',signal(),100);c.get_live_price=AsyncMock(return_value=108)
  d=dict(candle_time=STAMP+e.TF_MS,price_closed=107,atr=1,exit_signal=False)
  with patch.object(e,'frame',new=AsyncMock(return_value=d)):asyncio.run(e.manage_ema(c,'XRPUSDT'))
  self.assertEqual(c.positions['XRPUSDT']['stop_loss'],104)
  d.update(candle_time=STAMP+2*e.TF_MS,price_closed=106,atr=3)
  with patch.object(e,'frame',new=AsyncMock(return_value=d)):asyncio.run(e.manage_ema(c,'XRPUSDT'))
  self.assertEqual(c.positions['XRPUSDT']['stop_loss'],104)
  d.update(candle_time=STAMP+3*e.TF_MS,exit_signal=True)
  with patch.object(e,'frame',new=AsyncMock(return_value=d)):asyncio.run(e.manage_ema(c,'XRPUSDT'))
  self.assertEqual(c.trade_history[0]['reason'],'EMA 4h CROSS DOWN')
 def test_live_candle_does_not_repaint_and_gaps_fail(self):
  rows=[]
  for i in range(300):
   start=STAMP-(300-i)*e.TF_MS;p=100+i*.01
   rows.append([start,p,p+.1,p-.1,p,100,start+e.TF_MS-1])
  raw=rows+[[STAMP,100,10000,1,9999,100,STAMP+e.TF_MS-1]]
  a=e.analyze_rows(rows,STAMP+30000);b=e.analyze_rows(raw,STAMP+30000)
  self.assertEqual(a,b)
  with self.assertRaises(ValueError):e.analyze_rows(rows[:100]+rows[101:],STAMP+30000)
 def test_existing_core_still_has_no_time_exit(self):
  from pathlib import Path
  tree=ast.parse(Path('app_bestof_core.py').read_text())
  fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='manage_position')
  self.assertNotIn('TIME EXIT',ast.unparse(fn))

if __name__=='__main__':unittest.main()
