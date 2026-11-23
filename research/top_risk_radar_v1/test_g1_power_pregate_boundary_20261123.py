"""Boundary cases requested in ChatGPT review of PR #77 (2026-11-23): an episode
crossing the end of a fold's test year while its tail labels are unmatured.
Synthetic only, no market data."""
import unittest
from datetime import datetime, timedelta, timezone

from research.top_risk_radar_v1 import g1_power_pregate as pg

UTC = timezone.utc


def grid(end):
    out, d = [], datetime(2018, 5, 1, 0, 5, tzinfo=UTC)
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def mark(dec, first, last):
    lab = [False] * len(dec)
    for i, d in enumerate(dec):
        if first <= d.date() <= last:
            lab[i] = True
    return lab


def fold(r, year):
    return next(f for f in r["folds"] if f["test_year"] == year)


class BoundaryTests(unittest.TestCase):
    def test_cross_year_episode_with_unmatured_tail(self):
        # positives 2025-12-20 .. 2026-01-08; as_of 2026-01-20 => matured only through 2026-01-05
        as_of = datetime(2026, 1, 20, tzinfo=UTC)
        dec = grid(datetime(2026, 1, 19, 0, 5, tzinfo=UTC))
        lab = mark(dec, datetime(2025, 12, 20).date(), datetime(2026, 1, 8).date())
        r = pg.g1_power_pregate(dec, lab, as_of=as_of)
        self.assertEqual(fold(r, 2025)["grouped_positive_episodes"], 1)
        self.assertEqual(fold(r, 2026)["grouped_positive_episodes"], 1)
        self.assertEqual(r["pooled_grouped_positive_episodes"], 1)
        # 2026-01-06 .. 2026-01-19 are unmatured (14 rows) and are not test rows
        self.assertEqual(fold(r, 2026)["unmatured_rows"], 14)
        self.assertEqual(fold(r, 2026)["test_rows"], 5)

    def test_episode_entirely_in_unmatured_zone_not_counted(self):
        as_of = datetime(2026, 1, 10, tzinfo=UTC)  # 2025-12-27 00:05 + 14 d > as_of
        dec = grid(datetime(2026, 1, 9, 0, 5, tzinfo=UTC))
        lab = mark(dec, datetime(2025, 12, 29).date(), datetime(2026, 1, 2).date())
        r = pg.g1_power_pregate(dec, lab, as_of=as_of)
        self.assertEqual(r["pooled_grouped_positive_episodes"], 0)
        self.assertEqual(fold(r, 2025)["grouped_positive_episodes"], 0)
        self.assertGreater(fold(r, 2025)["unmatured_rows"], 0)

    def test_isolated_unmatured_burst_not_counted(self):
        # only the matured January burst counts; the unmatured February burst adds no episode
        as_of = datetime(2026, 3, 1, tzinfo=UTC)  # matured through 2026-02-15
        dec = grid(datetime(2026, 2, 28, 0, 5, tzinfo=UTC))
        lab = mark(dec, datetime(2026, 1, 10).date(), datetime(2026, 1, 12).date())
        for i, d in enumerate(dec):
            if datetime(2026, 2, 20).date() <= d.date() <= datetime(2026, 2, 22).date():
                lab[i] = True
        r = pg.g1_power_pregate(dec, lab, as_of=as_of)
        self.assertEqual(fold(r, 2026)["grouped_positive_episodes"], 1)

    def test_fingerprint_is_labels_only_not_provenance(self):
        # documents ChatGPT's open data gate: same labels => same hash regardless of source
        dec = grid(datetime(2022, 1, 10, 0, 5, tzinfo=UTC))
        lab = [False] * len(dec)
        self.assertEqual(pg.labels_fingerprint(dec, lab), pg.labels_fingerprint(list(dec), list(lab)))
        self.assertIn("necessary, not sufficient", pg.g1_power_pregate(dec, lab, as_of=datetime(2022, 2, 1, tzinfo=UTC))["note"])


if __name__ == "__main__":
    unittest.main()
