import copy,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import app_blue_whale_mirror as w

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.saved=copy.deepcopy(w.state)
  w.state.update(candidate_journal=[],market_prices={'XRPUSDT':100})
  self.now=datetime(2026,10,13,tzinfo=timezone.utc)
 def tearDown(self):w.state.clear();w.state.update(self.saved)
 def diag(self,key='k',side='LONG'):
  return dict(symbol='XRPUSDT',strategy='VWAP_REVERSION',candidate_key=key,side=side,
              candidate_entry=100,candidate_stop=99,candidate_target=102,reason='paused')
 def test_wait_scans_do_not_evict_candidates_and_repeats_are_counted(self):
  w.retain_candidates([self.diag()],self.now.isoformat())
  for _ in range(1500):w.retain_candidates([dict(symbol='XRPUSDT',strategy='FIB',reason='WAIT')],self.now.isoformat())
  w.retain_candidates([self.diag()],(self.now+timedelta(minutes=1)).isoformat())
  self.assertEqual(len(w.state['candidate_journal']),1)
  self.assertEqual(w.state['candidate_journal'][0]['observations'],2)
  self.assertEqual(w.state['candidate_journal'][0]['first_seen_at'],self.now.isoformat())
  w.retain_candidates([self.diag()],self.now.isoformat())
  self.assertEqual(w.state['candidate_journal'][0]['observations'],2)
  self.assertEqual(w._persistent_payload()['candidate_journal'],w.state['candidate_journal'])
 def test_different_symbols_and_strategies_are_distinct(self):
  a=self.diag();b={**a,'symbol':'ETHUSDT'};c={**a,'strategy':'FIB_618_786'}
  w.retain_candidates([a,b,c],self.now.isoformat())
  self.assertEqual(len(w.state['candidate_journal']),3)
 def test_followups_are_once_only_and_directional_for_both_sides(self):
  for side in ('LONG','SHORT'):
   w.state['candidate_journal']=[];w.retain_candidates([self.diag(side=side)],self.now.isoformat())
   for minute in (14,15,16,60,240):
    with patch.object(w,'utcnow',return_value=self.now+timedelta(minutes=minute)):
     w.observe_candidate_prices('XRPUSDT',102 if side=='LONG' else 98)
   r=w.state['candidate_journal'][0]
   self.assertEqual(set(r['followups']),{'15','60','240'})
   self.assertAlmostEqual(r['followups']['15']['directional_move_pct'],2)
   self.assertEqual(r['followups']['15']['actual_elapsed_minutes'],15)
   self.assertFalse(r['profitability_verified'])
 def test_late_quote_marks_missed_horizon_without_return(self):
  w.retain_candidates([self.diag()],self.now.isoformat())
  with patch.object(w,'utcnow',return_value=self.now+timedelta(minutes=40)):
   w.observe_candidate_prices('XRPUSDT',120)
  point=w.state['candidate_journal'][0]['followups']['15']
  self.assertTrue(point['missed']);self.assertNotIn('directional_move_pct',point)
 def test_marks_do_not_mutate_account_and_invalid_prices_are_ignored(self):
  before={k:copy.deepcopy(w.state[k]) for k in ('balance','equity','trades','open_positions')}
  w.retain_candidates([self.diag()],self.now.isoformat());snapshot=copy.deepcopy(w.state['candidate_journal'])
  for price in (0,-1,float('nan'),float('inf')):w.observe_candidate_prices('XRPUSDT',price)
  self.assertEqual(w.state['candidate_journal'],snapshot)
  with patch.object(w,'utcnow',return_value=self.now+timedelta(minutes=15)):w.observe_candidate_prices('XRPUSDT',102)
  for k,v in before.items():self.assertEqual(w.state[k],v)
 def test_unique_capacity(self):
  w.retain_candidates([self.diag(str(i)) for i in range(1100)],self.now.isoformat())
  self.assertEqual(len(w.state['candidate_journal']),1000)
  self.assertEqual(w.state['candidate_journal'][0]['candidate_key'],'100')

if __name__=='__main__':unittest.main()
