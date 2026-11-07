import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from research.top_risk_radar_v1.multiyear_census import evaluate

START=datetime(2024,1,1,tzinfo=timezone.utc)
def series(days, price=Decimal("1")):
    return [(START+timedelta(hours=h),price) for h in range(days*24)]

class MultiYearCensusTests(unittest.TestCase):
    def test_flat_prices_no_events(self):
        result=evaluate(series(32))
        self.assertEqual(result["per_decision_year"]["2024"]["growth"],0)
        self.assertEqual(result["per_decision_year"]["2024"]["risk"],0)
    def test_growth_episode(self):
        rows=series(33)
        rows=[(t,Decimal("1.40") if t>=START+timedelta(days=10) else p) for t,p in rows]
        result=evaluate(rows)
        self.assertGreater(result["per_decision_year"]["2024"]["growth"],0)
        self.assertEqual(len(result["growth_episodes_30d"]),1)
    def test_missing_hour_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate(series(32)[:10]+series(32)[11:])
    def test_duplicate_hour_fails_closed(self):
        rows=series(32)
        with self.assertRaises(ValueError):
            evaluate(rows+[rows[-1]])
