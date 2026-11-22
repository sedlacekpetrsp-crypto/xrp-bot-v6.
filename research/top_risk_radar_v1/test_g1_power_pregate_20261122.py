"""Synthetic tests for the G1 POWER NO-GO pre-gate. No market data."""
import inspect
import json
import unittest
from datetime import datetime, timedelta, timezone

from research.top_risk_radar_v1 import g1_power_pregate as pg

UTC = timezone.utc
AS_OF = datetime(2026, 11, 1, tzinfo=UTC)


def grid(start=datetime(2018, 5, 1, 0, 5, tzinfo=UTC), end=datetime(2026, 10, 1, 0, 5, tzinfo=UTC)):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def labels_with_episodes(decisions, starts, length=5):
    """Mark `length` consecutive positive days at each start date."""
    lab = [False] * len(decisions)
    pos = {d.date(): i for i, d in enumerate(decisions)}
    for s in starts:
        for k in range(length):
            lab[pos[(s + timedelta(days=k)).date()]] = True
    return lab


def yearly_starts(years, per_year):
    # episodes 60 days apart => always separate groups
    return [datetime(y, 2, 1, tzinfo=UTC) + timedelta(days=60 * k) for y in years for k in range(per_year)]


class PregateTests(unittest.TestCase):
    def setUp(self):
        self.dec = grid()

    def test_enough_episodes_power_ok(self):
        lab = labels_with_episodes(self.dec, yearly_starts([2022, 2023, 2024, 2025], 4))
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        self.assertEqual(r["verdict"], "POWER_OK")
        self.assertEqual(r["pooled_grouped_positive_episodes"], 16)
        self.assertEqual(r["evaluable_folds"], 4)

    def test_fourteen_pooled_is_no_go(self):
        lab = labels_with_episodes(self.dec, yearly_starts([2022, 2023], 4) + yearly_starts([2024, 2025], 3))
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        self.assertEqual(r["pooled_grouped_positive_episodes"], 14)
        self.assertEqual(r["verdict"], "POWER_NO_GO")
        self.assertIn("pooled_episodes_14_lt_15", r["reasons"])

    def test_concentrated_episodes_fail_fold_condition(self):
        # 16 pooled episodes but only 2 folds with >= 3
        lab = labels_with_episodes(self.dec, yearly_starts([2022, 2023], 6) + yearly_starts([2024, 2025], 2))
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        self.assertEqual(r["pooled_grouped_positive_episodes"], 16)
        self.assertEqual(r["evaluable_folds"], 2)
        self.assertEqual(r["verdict"], "POWER_NO_GO")
        self.assertEqual(r["reasons"], ["evaluable_folds_2_lt_3"])

    def test_explicit_14_day_separation_not_legacy_30(self):
        # two bursts 20 days apart (gap between last and first positive = 16 d) => 2 episodes at 14 d, 1 at 30 d
        lab = labels_with_episodes(self.dec, [datetime(2023, 3, 1, tzinfo=UTC), datetime(2023, 3, 21, tzinfo=UTC)])
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        f2023 = next(f for f in r["folds"] if f["test_year"] == 2023)
        self.assertEqual(f2023["grouped_positive_episodes"], 2)
        self.assertEqual(r["thresholds"]["episode_separation_days"], 14)

    def test_train_period_positives_ignored(self):
        lab = labels_with_episodes(self.dec, yearly_starts([2019, 2020, 2021], 5))
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        self.assertEqual(r["pooled_grouped_positive_episodes"], 0)
        self.assertEqual(r["verdict"], "POWER_NO_GO")

    def test_excluded_rows_do_not_count_or_form_episodes(self):
        lab = labels_with_episodes(self.dec, yearly_starts([2022, 2023, 2024, 2025], 4))
        lab = [None if v else v for v in lab]  # all positives excluded upstream
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        self.assertEqual(r["pooled_grouped_positive_episodes"], 0)
        self.assertEqual(sum(f["excluded_label_rows"] for f in r["folds"]), 80)

    def test_cross_year_episode_counted_once_pooled(self):
        lab = labels_with_episodes(self.dec, [datetime(2023, 12, 29, tzinfo=UTC)], length=6)
        r = pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)
        per = {f["test_year"]: f["grouped_positive_episodes"] for f in r["folds"]}
        self.assertEqual((per[2023], per[2024]), (1, 1))
        self.assertEqual(r["pooled_grouped_positive_episodes"], 1)

    def test_unmatured_rows_excluded(self):
        dec = grid(end=datetime(2026, 10, 30, 0, 5, tzinfo=UTC))
        lab = [False] * len(dec)
        r = pg.g1_power_pregate(dec, lab, as_of=AS_OF)
        f2026 = next(f for f in r["folds"] if f["test_year"] == 2026)
        self.assertGreater(f2026["unmatured_rows"], 0)

    def test_rejects_non_bool_labels(self):
        for bad in (1, 0, "1", 1.0):
            lab = [False] * len(self.dec)
            lab[100] = bad
            with self.assertRaises(ValueError):
                pg.g1_power_pregate(self.dec, lab, as_of=AS_OF)

    def test_rejects_length_mismatch_and_empty(self):
        with self.assertRaises(ValueError):
            pg.g1_power_pregate(self.dec, [False], as_of=AS_OF)
        with self.assertRaises(ValueError):
            pg.g1_power_pregate([], [], as_of=AS_OF)

    def test_naive_as_of_rejected(self):
        with self.assertRaises(ValueError):
            pg.g1_power_pregate(self.dec, [False] * len(self.dec), as_of=datetime(2026, 11, 1))

    def test_signature_has_no_features_or_predictions(self):
        params = set(inspect.signature(pg.g1_power_pregate).parameters)
        self.assertEqual(params, {"decisions", "labels", "as_of"})

    def test_artefact_deterministic_and_json(self):
        lab = labels_with_episodes(self.dec, yearly_starts([2022, 2023, 2024, 2025], 4))
        a = pg.dumps(pg.g1_power_pregate(self.dec, lab, as_of=AS_OF))
        b = pg.dumps(pg.g1_power_pregate(self.dec, list(lab), as_of=AS_OF))
        self.assertEqual(a, b)
        self.assertFalse(json.loads(a)["uses_predictions"])

    def test_fingerprint_sensitive_to_single_label(self):
        lab = [False] * len(self.dec)
        lab2 = list(lab)
        lab2[500] = None
        self.assertNotEqual(pg.labels_fingerprint(self.dec, lab), pg.labels_fingerprint(self.dec, lab2))


if __name__ == "__main__":
    unittest.main()
