import copy
import unittest
from unittest.mock import patch
import app_v9 as c
import paper_stop_policy as policy

class HunterStop(unittest.TestCase):
    def test_both_sides_keep_quantity_target_and_exit_threshold(self):
        for side in ('LONG','SHORT'):
            ps=[]
            for multiplier in (1.,1.15):
                with patch.object(policy,'MULTIPLIER',multiplier),patch.multiple(c,positions={},paper_balance=10000.,last_entry_candle={},save_state=lambda:None):
                    self.assertTrue(c.open_position('XRPUSDT',dict(signal=side,setup='LIQUIDITY_HUNTER_V2',candle_time=1),100,1))
                    ps.append(copy.deepcopy(c.positions['XRPUSDT']))
            a,b=ps
            self.assertEqual(a['qty'],b['qty']);self.assertEqual(a['take_profit'],b['take_profit'])
            self.assertEqual(a['initial_risk_distance'],b['initial_risk_distance'])
            self.assertAlmostEqual(abs(b['entry_price']-b['stop_loss']),1.15*abs(a['entry_price']-a['stop_loss']))
            self.assertGreater(b['stop_loss_risk_net'],0)

if __name__=='__main__':unittest.main()
