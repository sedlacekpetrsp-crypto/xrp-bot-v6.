import unittest
from datetime import datetime,timedelta,timezone
from research.top_risk_radar_v1.prevalence_baseline import Observation,historical_prevalence
T=datetime(2025,1,1,tzinfo=timezone.utc)
class PrevalenceBaselineTests(unittest.TestCase):
    def test_no_future_labels(self):
        rows=[Observation(T-timedelta(days=40),True,False),
              Observation(T-timedelta(days=5),False,True)]
        self.assertEqual(historical_prevalence(rows,T,horizon_days=30,target="growth")["rate"],1)
    def test_unknown_not_negative(self):
        rows=[Observation(T-timedelta(days=40),None,None)]
        self.assertEqual(historical_prevalence(rows,T,horizon_days=30,target="growth")["status"],"insufficient_train")
    def test_valid_rate(self):
        rows=[Observation(T-timedelta(days=40),True,False),
              Observation(T-timedelta(days=50),False,True)]
        self.assertEqual(historical_prevalence(rows,T,horizon_days=14,target="downside")["rate"],0.5)
    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            historical_prevalence([],T,horizon_days=14,target="price")
