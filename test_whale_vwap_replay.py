import bisect,unittest,copy,hashlib,contextlib,io
from datetime import datetime,timezone
from unittest.mock import patch
from test_exit_regressions import functions
import app_blue_whale_mirror as w
PATH='research/whale_vwap_validation_20261013/run.py'

class ReplayTests(unittest.TestCase):
 def test_hypotheses_fail_closed_and_do_not_mutate_inputs(self):
  f=functions(PATH,{'passes'}, {})['passes']
  item={'review':{'rsi_available':True,'extreme_rsi_would_block':True,'continuation_5m':True}}
  old=copy.deepcopy(item)
  self.assertTrue(f(item,'baseline'));self.assertFalse(f(item,'rsi_extremes'))
  item['review']['extreme_rsi_would_block']=False;item['review']['continuation_5m']=False
  self.assertTrue(f(item,'rsi_extremes'));self.assertFalse(f(item,'rsi_and_5m_continuation'))
  item['review']['rsi_available']=False;self.assertFalse(f(item,'rsi_extremes'))
  self.assertTrue(old['review']['extreme_rsi_would_block'])
 def test_only_closed_candles_are_visible(self):
  rows=[[0,100,200,1,199,10,59999],[60000,199,999,.1,900,100,119999]]
  env={'frames':{'ETHUSDT':{'1m':rows}},'ends':{'ETHUSDT':{'1m':[59999,119999]}},'clock':[60000],'bisect':bisect}
  f=functions(PATH,{'closed_rows'},env)['closed_rows']
  self.assertEqual(f('ETHUSDT','1m'),[rows[0]])
  rows[1][4]=100000;self.assertEqual(f('ETHUSDT','1m'),[rows[0]])
 def run_sample(self,gap=False):
  start=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
  candidate=dict(side='LONG',entry=100,stop=99,tp=104,key='vwap:test',strategy='VWAP_REVERSION')
  bars=[[start,100,100.1,99.5,100,10,start+59999],
        [start+60000,97 if gap else 100,105,96,100,10,start+119999]]
  clock=[start]
  env={'w':w,'symbols':['ETHUSDT','SOLUSDT'],'data':{s:copy.deepcopy(bars) for s in ['ETHUSDT','SOLUSDT']},
       'clock':clock,'copy':copy,'hashlib':hashlib,'protocol':{'shared_reference_balance':9178.2},'passes':lambda *a:True}
  replay=functions(PATH,{'replay'},env)['replay']
  saved=copy.deepcopy(w.state)
  with patch.object(w,'PAUSED_STRATEGIES',frozenset()),patch.object(w,'DATABASE_URL',None),patch.object(w,'save_state',lambda:None),patch.object(w,'save_trade',lambda t:None),patch.object(w,'utcnow',lambda:datetime.fromtimestamp(clock[0]/1000,timezone.utc)),patch.object(w,'portfolio_entry_allowed',lambda *a:(True,''),create=True),patch.object(w,'portfolio_risk_allowance',lambda *a:(9,{}),create=True),contextlib.redirect_stdout(io.StringIO()):
   try:
    result,trades=replay({str(start):[{'symbol':'ETHUSDT','candidate':candidate}]},start,start+120000,'baseline',.0002)
   finally:w.state.clear();w.state.update(saved)
  return result,trades
 def test_simultaneous_stop_and_target_prefers_stop_and_costs_reconcile(self):
  r,tr=self.run_sample();self.assertEqual(len(tr),1);self.assertEqual(tr[0]['reason'],'SL')
  self.assertLess(r['net_pnl'],0);self.assertAlmostEqual(r['net_pnl'],sum(t['net_pnl'] for t in tr))
 def test_adverse_gap_uses_open(self):
  r,tr=self.run_sample(True);self.assertEqual(tr[0]['reason'],'GAP STOP')
  self.assertAlmostEqual(tr[0]['exit'],97*(1-.0002))

if __name__=='__main__':unittest.main()
