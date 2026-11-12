"""Synthetic E2E contract for P3 pipeline; no market data, no performance test."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone

import pytest

from research.top_risk_radar_v1.pipeline import (
    COLUMNS, Fold, PredictionInput, build_predictions, run_pipeline,
)

UTC = timezone.utc
T0 = datetime(2025, 1, 1, tzinfo=UTC)
H = timedelta(hours=336)
EVAL = datetime(2026, 11, 1, tzinfo=UTC)


def inp(i, day, label, p=0.3, early_days=None):
    d = T0 + timedelta(days=day)
    avail = d + (timedelta(days=early_days) if early_days is not None else H)
    return PredictionInput(f"e{i:03d}", d, avail, label, p, f"h{i}")


def rows(n=120, p_pos=0.7, p_neg=0.1):
    out = []
    for i in range(n):
        label = 1 if i % 4 == 0 else 0
        out.append(inp(i, 3 * i, label, p_pos if label else p_neg))
    return out


FOLDS = [Fold("f1", T0 + timedelta(days=180), T0 + timedelta(days=270)),
         Fold("f2", T0 + timedelta(days=270), T0 + timedelta(days=360))]


def test_e2e_deterministic_and_schema():
    a = run_pipeline(rows(), FOLDS, target="downside", evaluated_at=EVAL, bootstrap=200)
    b = run_pipeline(list(reversed(rows())), FOLDS, target="downside", evaluated_at=EVAL, bootstrap=200)
    assert a == b
    reader = list(csv.reader(io.StringIO(a["predictions_csv"].decode())))
    assert tuple(reader[0]) == COLUMNS and len(reader) == 121
    s = json.loads(a["scoring_json"])
    assert s["predictions_sha256"] == a["predictions_sha256"]
    assert s["n_scored"] == 60 and s["excluded"] == {"outside_test_folds": 60}
    assert s["verdict"] == "DIAGNOSTIC_SKILL_POSITIVE" and s["brier_skill_ci95"][0] > 0
    assert s["eps"] is None and s["bootstrap_unit"] == "episode_id"


def test_reference_is_train_only_per_fold():
    recs = build_predictions(rows(), FOLDS, target="downside", evaluated_at=EVAL)
    f1 = {r["p_ref"] for r in recs if r["fold"] == "f1"}
    f2 = {r["p_ref"] for r in recs if r["fold"] == "f2"}
    assert len(f1) == 1 and len(f2) == 1
    # f1 train: decisions with decision+horizon < test_start (day 180) => days 0..165 (56 rows)
    assert f1 == {14 / 56}


def test_test_label_change_does_not_move_reference():
    base = rows()
    flipped = [inp(int(r.episode_id[1:]), (r.decision_at - T0).days, 1 - r.label)
               if r.decision_at >= FOLDS[1].test_start else r for r in base]
    a = build_predictions(base, FOLDS, target="downside", evaluated_at=EVAL)
    b = build_predictions(flipped, FOLDS, target="downside", evaluated_at=EVAL)
    assert [r["p_ref"] for r in a] == [r["p_ref"] for r in b]


def test_immature_missing_never_coerced_to_zero():
    data = rows()
    late = T0 + timedelta(days=195)
    data[61] = inp(61, 183, 0)            # negative maturing after EVAL below
    data[62] = PredictionInput("e062", T0 + timedelta(days=186), T0 + timedelta(days=200), None, 0.2, "h")
    recs = build_predictions(data, FOLDS, target="downside", evaluated_at=late)
    by = {r["episode_id"]: r for r in recs}
    assert by["e061"]["exclusion_reason"] == "label_immature" and by["e061"]["y"] is None
    assert by["e062"]["exclusion_reason"] == "label_missing" and by["e062"]["y"] is None


def test_early_positive_scored_but_premature_negative_rejected():
    data = rows()
    data[70] = inp(70, 210, 1, early_days=5)
    recs = build_predictions(data, FOLDS, target="downside", evaluated_at=T0 + timedelta(days=216))
    r = next(x for x in recs if x["episode_id"] == "e070")
    assert r["y"] == 1 and r["exclusion_reason"] == ""
    data[71] = inp(71, 213, 0, early_days=5)
    with pytest.raises(ValueError, match="premature_label_availability"):
        build_predictions(data, FOLDS, target="downside", evaluated_at=EVAL)


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), 1.5, -0.1, "0.3"])
def test_invalid_model_probability_fails_closed(bad):
    data = rows()
    data[0] = PredictionInput("e000", T0, T0 + H, 1, bad, "h")
    with pytest.raises(ValueError, match="invalid_p_model"):
        build_predictions(data, FOLDS, target="downside", evaluated_at=EVAL)


def test_bool_label_and_duplicates_and_overlap_rejected():
    data = rows()
    data[0] = PredictionInput("e000", T0, T0 + H, True, 0.3, "h")
    with pytest.raises(ValueError):
        build_predictions(data, FOLDS, target="downside", evaluated_at=EVAL)
    with pytest.raises(ValueError, match="duplicate_episode_id"):
        build_predictions(rows() + [rows()[0]], FOLDS, target="downside", evaluated_at=EVAL)
    with pytest.raises(ValueError, match="overlapping_folds"):
        build_predictions(rows(), [FOLDS[0], Fold("x", T0 + timedelta(days=200), T0 + timedelta(days=300))],
                          target="downside", evaluated_at=EVAL)


def test_nonfinite_log_loss_serialized_as_null_with_reason():
    data = [inp(i, 3 * i, 1 if i % 4 == 0 else 0, 0.0) for i in range(120)]
    out = run_pipeline(data, FOLDS, target="downside", evaluated_at=EVAL, bootstrap=50)
    s = json.loads(out["scoring_json"])
    assert s["model"]["log_loss"] is None and s["model"]["log_loss_nonfinite_reason"] == "inf"
    out_eps = run_pipeline(data, FOLDS, target="downside", evaluated_at=EVAL, bootstrap=50, eps=1e-6)
    s2 = json.loads(out_eps["scoring_json"])
    assert s2["eps"] == 1e-6 and s2["model"]["log_loss"] is not None


def test_uninformative_model_is_inconclusive_not_success():
    data = [inp(i, 3 * i, 1 if i % 4 == 0 else 0, 0.25) for i in range(120)]
    s = json.loads(run_pipeline(data, FOLDS, target="downside", evaluated_at=EVAL, bootstrap=200)["scoring_json"])
    assert s["verdict"] == "INCONCLUSIVE"


def test_no_mature_rows():
    s = json.loads(run_pipeline(rows(), FOLDS, target="downside", evaluated_at=T0, bootstrap=10)["scoring_json"])
    assert s["n_scored"] == 0 and s["verdict"] == "INCONCLUSIVE_NO_MATURE_ROWS"
