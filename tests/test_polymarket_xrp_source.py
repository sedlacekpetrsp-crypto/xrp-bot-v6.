import datetime as dt
import json
import unittest

from research.polymarket_xrp_source import UTC, coverage_decision, validate_events, validate_market, validate_series, validate_trades


class Tests(unittest.TestCase):
    def test_series_identity(self):
        payload = json.dumps([{"id": "1", "slug": "xrp-up-or-down-5m", "recurrence": "5m", "createdAt": "2025-11-21T00:00:00Z", "active": True}])
        self.assertEqual(validate_series(payload)["id"], "1")

    def test_market_token_mapping(self):
        payload = json.dumps({"outcomes": '["Up","Down"]', "clobTokenIds": '["u","d"]', "conditionId": "c", "volume": "100", "events": [{"seriesSlug": "xrp-up-or-down-5m", "resolutionSource": "https://data.chain.link/streams/xrp-usd", "startTime": "2026-01-01T00:00:00Z", "endDate": "2026-01-01T00:05:00Z"}]})
        self.assertEqual(validate_market(payload)["up_token"], "u")

    def test_event_duration_and_order(self):
        rows = [{"slug": f"xrp-updown-5m-{i}", "closed": True, "startTime": f"2026-01-01T00:{i:02d}:00Z", "endDate": f"2026-01-01T00:{i+5:02d}:00Z"} for i in (0, 5)]
        self.assertEqual(len(validate_events(json.dumps(rows))), 2)

    def test_trade_causality_fields(self):
        market = {"condition_id": "c", "up_token": "u", "down_token": "d"}
        rows = [{"conditionId": "c", "asset": "u", "price": .7, "size": 2, "timestamp": 20}, {"conditionId": "c", "asset": "d", "price": .3, "size": 1, "timestamp": 10}]
        self.assertEqual(len(validate_trades(json.dumps(rows), market)), 2)

    def test_insufficient_history_is_incomplete_not_rejected(self):
        series = {"created_at": dt.datetime(2025, 11, 21, tzinfo=UTC)}
        result = coverage_decision(series, dt.datetime(2025, 12, 18, tzinfo=UTC), dt.datetime(2026, 10, 29, tzinfo=UTC))
        self.assertFalse(result["source_pass"])
        self.assertLess(result["available_days"], 730)

    def test_bad_market_is_rejected(self):
        payload = json.dumps({"outcomes": '["Down","Up"]', "clobTokenIds": '["d","u"]', "conditionId": "c", "volume": "1", "events": [{}]})
        with self.assertRaises(ValueError):
            validate_market(payload)


if __name__ == "__main__":
    unittest.main()
