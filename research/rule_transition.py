"""Fail-closed paired PIT audit of historical exchange-rule transitions; no PnL."""
from decimal import Decimal, InvalidOperation
from research.exchange_rule_pit import rule_asof, _utc


def audit_transition(snapshots, *, venue, symbol, rule, before_at, after_at):
    before, after = _utc(before_at), _utc(after_at)
    if before >= after:
        raise ValueError("before_at must precede after_at")
    params = dict(venue=venue, symbol=symbol, rule=rule)
    old = rule_asof(snapshots, decision_at=before, **params)
    new = rule_asof(snapshots, decision_at=after, **params)
    if old["status"] != "DATA_GO" or new["status"] != "DATA_GO":
        return {"status": "DATA_NO_GO", "reason": "missing_paired_pit_evidence"}
    try:
        a, b = Decimal(old["value"]), Decimal(new["value"])
    except (InvalidOperation, ValueError, TypeError):
        return {"status": "DATA_NO_GO", "reason": "non_numeric_rule"}
    if not a.is_finite() or not b.is_finite() or a <= 0 or b <= 0:
        return {"status": "DATA_NO_GO", "reason": "non_positive_or_nonfinite_rule"}
    if old["effective_at"] > new["effective_at"]:
        return {"status": "DATA_NO_GO", "reason": "non_monotonic_effective_time"}
    return {"status": "DATA_GO", "changed": a != b, "old": str(a), "new": str(b),
            "ratio": str(b / a), "before_evidence_hash": old["evidence_hash"],
            "after_evidence_hash": new["evidence_hash"],
            "observed_between": (before.isoformat(), after.isoformat())}
