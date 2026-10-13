import copy,unittest
from unittest.mock import patch
import app_blue_whale_mirror as w

class ReversionTests(unittest.TestCase):
 def setUp(self):
  self.saved=copy.deepcopy(w.state)
 def tearDown(self):
  w.state.clear();w.state.update(self.saved)
 def test_all_reversion_entries_are_blocked_without_account_changes(self):
  for side in ('LONG','SHORT'):
   before=copy.deepcopy(w.state)
   self.assertFalse(w.open_paper({'strategy':'VWAP_REVERSION','id':123},side,100))
   for key in ('balance','equity','open_positions','trades','seen_signal_ids'):
    self.assertEqual(w.state[key],before[key])
   self.assertIn('pozastavena',w.state['last_signal']['rejected'])
 def test_actual_extreme_short_cases_fail_shadow_hypotheses(self):
  candidate=dict(side='SHORT',entry=100,tp=98)
  for rsi in (11.300448430493304,13.878562577447411):
   d=w.reversion_review(candidate,{'details':{'1h':{'rsi':rsi},'5m':{'close':100,'ema20':99,'ema50':98,'ret3':.005}}})
   self.assertTrue(d['extreme_rsi_would_block']);self.assertFalse(d['continuation_5m'])
   self.assertFalse(d['profitability_verified'])
 def test_aligned_short_and_long_and_missing_data(self):
  for side,rsi,close,e20,e50,ret,tp in [('SHORT',40,98,99,100,-.01,95),('LONG',60,102,101,100,.01,105)]:
   d=w.reversion_review(dict(side=side,entry=100,tp=tp),{'details':{'1h':{'rsi':rsi},'5m':dict(close=close,ema20=e20,ema50=e50,ret3=ret)}})
   self.assertFalse(d['extreme_rsi_would_block']);self.assertTrue(d['continuation_5m'])
   self.assertGreater(d['target_net_rate'],0)
  d=w.reversion_review(dict(side='SHORT',entry=100,tp=99.99),{})
  self.assertFalse(d['rsi_available']);self.assertFalse(d['continuation_5m'])
  self.assertLess(d['target_net_rate'],0)
 def test_shadow_review_does_not_change_inputs_or_account(self):
  candidate=dict(side='LONG',entry=100,tp=104);tech={'details':{'1h':{'rsi':90}}}
  before=copy.deepcopy((candidate,tech,w.state))
  w.reversion_review(candidate,tech)
  self.assertEqual((candidate,tech,w.state),before)
 def test_other_strategies_are_not_paused(self):
  self.assertNotIn('FIB_618_786',w.PAUSED_STRATEGIES)
  self.assertNotIn('VWAP_TREND_RECLAIM',w.PAUSED_STRATEGIES)
  self.assertNotIn(w.whale_trendline.STRATEGY,w.PAUSED_STRATEGIES)

if __name__=='__main__':unittest.main()
