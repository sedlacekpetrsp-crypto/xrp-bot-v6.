import unittest
from unittest.mock import patch
from collect_snapshot import capture


class CollectorTests(unittest.TestCase):
    def test_empty_market_is_unusable(self):
        with patch('collect_snapshot.get',return_value={'status':200,'data':[]}):
            r=capture('xrp-updown-5m-300')
        self.assertFalse(r['usable'])

    def test_token_mapping_uses_outcome_not_position(self):
        def fake(url):
            if 'gamma-api' in url:
                return {'data':[{'slug':'xrp-updown-5m-300','outcomes':'["Down","Up"]','clobTokenIds':'["10","20"]'}]}
            return dict(url=url,status=200,data={},requested_at=350,received_at=351)
        with patch('collect_snapshot.get',side_effect=fake):
            r=capture('xrp-updown-5m-300')
        self.assertEqual(r['up_token'],'20')
        self.assertIn('token_id=20',r['observations'][0]['url'])
        self.assertFalse(r['usable'])

    def test_wrong_asset_rejected(self):
        with self.assertRaises(ValueError):capture('btc-updown-5m-300')
