import unittest
from research.k13_tier_domain import validate_tier_snapshot


def rows():
    return [
        dict(tier=1, notional_cap="50000", maintenance_margin_rate="0.004", max_leverage="50"),
        dict(tier=2, notional_cap="250000", maintenance_margin_rate="0.01", max_leverage="25"),
    ]


class TierDomainTests(unittest.TestCase):
    def check(self, mutate, expected):
        r = rows()
        mutate(r)
        self.assertEqual(validate_tier_snapshot(r)["reason"], expected)

    def test_valid(self):
        self.assertEqual(validate_tier_snapshot(rows())["reason"], "internal_consistency_only")

    def test_empty(self):
        self.assertEqual(validate_tier_snapshot([])["reason"], "empty_or_invalid")

    def test_duplicate_tier(self):
        self.check(lambda r: r[1].update(tier=1), "tier_sequence")

    def test_bool_tier(self):
        self.check(lambda r: r[0].update(tier=True), "tier_sequence")

    def test_unknown_field(self):
        self.check(lambda r: r[0].update(unverified=True), "invalid_schema")

    def test_nan(self):
        self.check(lambda r: r[0].update(notional_cap="NaN"), "invalid_numeric")

    def test_zero_cap(self):
        self.check(lambda r: r[0].update(notional_cap=0), "invalid_numeric")

    def test_rate_over_one(self):
        self.check(lambda r: r[0].update(maintenance_margin_rate="1.1"), "out_of_domain")

    def test_leverage_below_one(self):
        self.check(lambda r: r[0].update(max_leverage="0.5"), "out_of_domain")

    def test_cap_decreases(self):
        self.check(lambda r: r[1].update(notional_cap="100"), "nonmonotonic_risk_tiers")

    def test_mmr_decreases(self):
        self.check(lambda r: r[1].update(maintenance_margin_rate="0.001"), "nonmonotonic_risk_tiers")

    def test_leverage_increases(self):
        self.check(lambda r: r[1].update(max_leverage="100"), "leverage_increases_with_tier")


if __name__ == "__main__":
    unittest.main()
