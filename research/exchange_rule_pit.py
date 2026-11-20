"""PAPER-only data-first audit of exchange rule changes; no trading or PnL.

A rule is usable only when its archived evidence was captured no later than the
decision and its exchange effective time is no later than the decision.
Unknown rules fail closed, never fall back to today's exchange metadata.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class RuleSnapshot:
    venue: str
    symbol: str
    rule: str
    value: str
    published_at: datetime
    captured_at: datetime
    effective_at: datetime
    evidence_hash: str


def _utc(t):
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return t.astimezone(timezone.utc)


def rule_asof(snapshots, *, venue, symbol, rule, decision_at):
    """Return frozen rule evidence or DATA_NO_GO with an explicit reason.

    Evidence is append-only. A late archive of an earlier effective rule does
    not become retrospectively visible. Conflicting values at the same latest
    effective time are not arbitrarily resolved.
    """
    decision = _utc(decision_at)
    if not all(isinstance(x, str) and x.strip() for x in (venue, symbol, rule)):
        raise ValueError("nonempty venue/symbol/rule required")
    candidates = []
    for s in snapshots:
        if not isinstance(s, RuleSnapshot):
            raise ValueError("invalid snapshot")
        pub, cap, eff = map(_utc, (s.published_at, s.captured_at, s.effective_at))
        if not all(isinstance(x, str) and x.strip() for x in
                   (s.venue, s.symbol, s.rule, s.value, s.evidence_hash)):
            raise ValueError("missing provenance")
        if (s.venue, s.symbol, s.rule) != (venue, symbol, rule):
            continue
        if pub > cap:
            raise ValueError("capture before publication")
        if pub <= decision and cap <= decision and eff <= decision:
            candidates.append((eff, cap, s))
    if not candidates:
        return {"status": "DATA_NO_GO", "reason": "no_pit_evidence"}
    latest_effective = max(x[0] for x in candidates)
    eligible = [x for x in candidates if x[0] == latest_effective]
    values = {x[2].value for x in eligible}
    if len(values) != 1:
        return {"status": "DATA_NO_GO", "reason": "conflicting_rule_evidence"}
    chosen = max(eligible, key=lambda x: (x[1], x[2].evidence_hash))[2]
    return {"status": "DATA_GO", "value": chosen.value,
            "effective_at": latest_effective.isoformat(),
            "captured_at": _utc(chosen.captured_at).isoformat(),
            "evidence_hash": chosen.evidence_hash}


def minimum_roundtrip_cost(bps_fee_each_side, bps_slippage_each_side):
    """Mechanical cost floor, not an alpha or profitability estimate."""
    try:
        fee = Decimal(str(bps_fee_each_side))
        slip = Decimal(str(bps_slippage_each_side))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid cost")
    if not fee.is_finite() or not slip.is_finite() or min(fee, slip) < 0:
        raise ValueError("nonnegative finite costs required")
    return 2 * (fee + slip)
