import unittest
from research.k13_tier_evidence import tier_change_evidence


def sample():
    return dict(venue="Binance", market="usdt_perpetual", symbol="XRPUSDT",
                tier=1, source_id="archive-001",
                before={"max_leverage": "50"}, after={"max_leverage": "25"})


class EvidenceTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(tier_change_evidence(sample())["ok"])

    def test_no_change(self):
        r = sample(); r["after"] = {"max_leverage": "50"}
        self.assertEqual(tier_change_evidence(r)["reason"], "no_demonstrated_change")

    def test_spot_market(self):
        r = sample(); r["market"] = "spot"
        self.assertEqual(tier_change_evidence(r)["reason"], "market_mismatch")

    def test_unpaired(self):
        r = sample(); r["after"] = {}
        self.assertEqual(tier_change_evidence(r)["reason"], "unpaired_metric")

    def test_nonfinite(self):
        r = sample(); r["after"] = {"max_leverage": "NaN"}
        self.assertEqual(tier_change_evidence(r)["reason"], "bad_metric")

    def test_negative(self):
        r = sample(); r["before"] = {"max_leverage": "-1"}
        self.assertEqual(tier_change_evidence(r)["reason"], "bad_metric")

    def test_bool_tier(self):
        r = sample(); r["tier"] = True
        self.assertEqual(tier_change_evidence(r)["reason"], "bad_tier")

    def test_missing_source(self):
        r = sample(); del r["source_id"]
        self.assertEqual(tier_change_evidence(r)["reason"], "missing_field")

    def test_empty_identity(self):
        r = sample(); r["source_id"] = " "
        self.assertEqual(tier_change_evidence(r)["reason"], "bad_identity")

    def test_not_record(self):
        self.assertEqual(tier_change_evidence(None)["reason"], "bad_record")


if __name__ == "__main__":
    unittest.main()
