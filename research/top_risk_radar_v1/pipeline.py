"""P3 synthetic end-to-end pipeline for the XRP PAPER radars (DELIVERY-01, 0296 §2, 0299).

Wires P2 baseline M0 (train-only) and P1 scoring (`calibration_metrics.score`, the only
scoring API) into a versioned `predictions.csv` + scoring JSON. Diagnostic only:
no market I/O, no model fit beyond M0, no trading signal, no OOS claim.

Contract (PREDICTIONS_SCHEMA "radar-predictions-v1"):
- every input row produces exactly one predictions.csv row; excluded rows keep an
  explicit `exclusion_reason` and empty y/p (never coerced to 0);
- y is int 0/1 only from an explicit mature label: positive may mature early (but
  after its decision), negative only after the full horizon; both must be available
  at or before `evaluated_at`;
- p_ref comes from M0 fitted on train rows strictly before the fold's test_start;
- scoring uses identical rows for model and reference; JSON uses allow_nan=False,
  non-finite metrics become null + `nonfinite_reason`; `eps` is always reported;
- Brier skill CI: deterministic bootstrap over episodes (episode_id), not rows;
- outputs are byte-deterministic; SHA-256 of both artefacts is returned (acceptance #7).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from .baselines import BASELINE_VERSION, HORIZON_HOURS, LabelRow, fit_m0
from .calibration_metrics import SCORING_VERSION, brier_skill_score, score

PREDICTIONS_SCHEMA = "radar-predictions-v1"
PIPELINE_VERSION = "radar-p3-synthetic-v1"
COLUMNS = (
    "schema_version", "episode_id", "target", "horizon_h", "fold", "decision_at_utc",
    "label_available_at_utc", "label_source_type", "maturity", "y", "p_model", "p_ref",
    "ref_version", "feature_hash", "exclusion_reason",
)
UTC = timezone.utc


@dataclass(frozen=True)
class PredictionInput:
    episode_id: str
    decision_at: datetime
    label_available_at: datetime
    label: int | None
    p_model: float
    feature_hash: str


@dataclass(frozen=True)
class Fold:
    name: str
    test_start: datetime
    test_end: datetime  # exclusive


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(value: float | None) -> str:
    return "" if value is None else repr(float(value))


def _maturity(row: PredictionInput, horizon: timedelta, evaluated_at: datetime) -> str:
    if row.label is None:
        return "missing"
    if type(row.label) is not int or row.label not in (0, 1):
        raise ValueError("invalid_label")
    decision, available = _utc(row.decision_at), _utc(row.label_available_at)
    if row.label == 1 and available <= decision:
        raise ValueError("premature_label_availability")
    if row.label == 0 and available < decision + horizon:
        raise ValueError("premature_label_availability")
    return "mature" if available <= evaluated_at else "immature"


def build_predictions(
    rows: Sequence[PredictionInput], folds: Sequence[Fold], *, target: str, evaluated_at: datetime
) -> list[dict]:
    if target not in HORIZON_HOURS:
        raise ValueError("unknown_target")
    horizon = timedelta(hours=HORIZON_HOURS[target])
    evaluated = _utc(evaluated_at)
    ids = [r.episode_id for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate_episode_id")
    ordered = sorted(folds, key=lambda f: _utc(f.test_start))
    for a, b in zip(ordered, ordered[1:]):
        if _utc(b.test_start) < _utc(a.test_end):
            raise ValueError("overlapping_folds")
    out: list[dict] = []
    for row in sorted(rows, key=lambda r: (_utc(r.decision_at), r.episode_id)):
        p = row.p_model
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(float(p)) \
                or not 0.0 <= float(p) <= 1.0:
            raise ValueError("invalid_p_model")
        decision = _utc(row.decision_at)
        maturity = _maturity(row, horizon, evaluated)
        fold = next((f for f in ordered if _utc(f.test_start) <= decision < _utc(f.test_end)), None)
        reason, p_ref, y = "", None, None
        if fold is None:
            reason = "outside_test_folds"
        else:
            train = [LabelRow(r.decision_at, r.label_available_at, r.label) for r in rows
                     if _utc(r.decision_at) < _utc(fold.test_start)]
            m0 = fit_m0(train, target=target, test_start=fold.test_start)
            p_ref = m0["probability"]
            if maturity != "mature":
                reason = f"label_{maturity}"
            elif p_ref is None:
                reason = "reference_insufficient_train"
            else:
                y = row.label
        out.append({
            "schema_version": PREDICTIONS_SCHEMA, "episode_id": row.episode_id, "target": target,
            "horizon_h": HORIZON_HOURS[target], "fold": fold.name if fold else "",
            "decision_at_utc": _iso(row.decision_at), "label_available_at_utc": _iso(row.label_available_at),
            "label_source_type": "none" if row.label is None else "explicit_int",
            "maturity": maturity, "y": y, "p_model": float(p), "p_ref": p_ref,
            "ref_version": BASELINE_VERSION, "feature_hash": row.feature_hash, "exclusion_reason": reason,
        })
    return out


def predictions_csv(records: Sequence[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(COLUMNS)
    for r in records:
        writer.writerow([
            _fmt(r[c]) if c in ("p_model", "p_ref") else ("" if r[c] is None else str(r[c]))
            for c in COLUMNS
        ])
    return buf.getvalue().encode("utf-8")


def _finite(record: dict, key: str, value: float | None) -> None:
    if value is not None and not math.isfinite(value):
        record[key] = None
        record[f"{key}_nonfinite_reason"] = "inf" if value > 0 else ("-inf" if value < 0 else "nan")
    else:
        record[key] = value


def score_predictions(
    records: Sequence[dict], *, eps: float | None = None, bootstrap: int = 1000, seed: int = 20261112,
    bins: int = 10,
) -> dict:
    used = [r for r in records if not r["exclusion_reason"]]
    excluded: dict[str, int] = {}
    for r in records:
        if r["exclusion_reason"]:
            excluded[r["exclusion_reason"]] = excluded.get(r["exclusion_reason"], 0) + 1
    result: dict = {"pipeline_version": PIPELINE_VERSION, "predictions_schema": PREDICTIONS_SCHEMA,
                    "scoring_version": SCORING_VERSION, "status": "diagnostic_only",
                    "n_rows": len(records), "n_scored": len(used),
                    "excluded": dict(sorted(excluded.items())), "eps": eps,
                    "n_episodes": len({r["episode_id"] for r in used})}
    if not used:
        result.update(model=None, reference=None, brier_skill=None, brier_skill_ci95=None,
                      verdict="INCONCLUSIVE_NO_MATURE_ROWS")
        return result
    p = [r["p_model"] for r in used]
    q = [r["p_ref"] for r in used]
    y = [r["y"] for r in used]
    model = score(p, y, bins=bins, eps=eps)
    ref = score(q, y, bins=bins, eps=eps)
    for s in (model, ref):
        _finite(s, "log_loss", s["log_loss"])
    _finite(result, "brier_skill", brier_skill_score(p, q, y))
    if result["brier_skill"] is None and "brier_skill_nonfinite_reason" not in result:
        result["brier_skill_nonfinite_reason"] = "reference_perfect"
    rng = random.Random(seed)
    idx = list(range(len(used)))
    stats: list[float] = []
    for _ in range(bootstrap):
        sample = [idx[rng.randrange(len(idx))] for _ in idx]
        value = brier_skill_score([p[i] for i in sample], [q[i] for i in sample], [y[i] for i in sample])
        if value is not None and math.isfinite(value):
            stats.append(value)
    stats.sort()
    ci = None
    if len(stats) >= max(20, bootstrap // 2):
        ci = [stats[int(0.025 * (len(stats) - 1))], stats[int(0.975 * (len(stats) - 1))]]
    result.update(model=model, reference=ref, brier_skill_ci95=ci, bootstrap=bootstrap, seed=seed,
                  bootstrap_unit="episode_id", bootstrap_valid=len(stats))
    if ci is None or ci[0] <= 0.0 <= ci[1]:
        result["verdict"] = "INCONCLUSIVE"
    else:
        result["verdict"] = "DIAGNOSTIC_SKILL_POSITIVE" if ci[0] > 0 else "DIAGNOSTIC_SKILL_NEGATIVE"
    return result


def run_pipeline(
    rows: Sequence[PredictionInput], folds: Sequence[Fold], *, target: str, evaluated_at: datetime,
    eps: float | None = None, bootstrap: int = 1000, seed: int = 20261112,
) -> dict:
    """Return byte-deterministic artefacts and their SHA-256 (acceptance check #7)."""
    records = build_predictions(rows, folds, target=target, evaluated_at=evaluated_at)
    csv_bytes = predictions_csv(records)
    scoring = score_predictions(records, eps=eps, bootstrap=bootstrap, seed=seed)
    scoring["predictions_sha256"] = hashlib.sha256(csv_bytes).hexdigest()
    scoring_bytes = json.dumps(scoring, sort_keys=True, allow_nan=False,
                               separators=(",", ":")).encode("utf-8")
    return {"predictions_csv": csv_bytes, "scoring_json": scoring_bytes,
            "predictions_sha256": scoring["predictions_sha256"],
            "scoring_sha256": hashlib.sha256(scoring_bytes).hexdigest()}
