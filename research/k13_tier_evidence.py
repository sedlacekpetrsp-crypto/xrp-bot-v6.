"""K13 conservative diagnostic of tier-change evidence; DATA ONLY, not a trading signal.

A tier number alone, or an isolated percentage, is not proof of a rule transition.
This diagnostic intentionally requires explicit structured before/after records.
"""
from decimal import Decimal, InvalidOperation


def _positive(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("invalid_numeric_type")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("invalid_decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("nonpositive_or_nonfinite")
    return number


def tier_change_evidence(record):
    """Require same venue/market/symbol/tier and an actual numeric rule change.

    The input is a manually extracted, independently reviewable record; this
    function does NOT certify publication timestamps or source authenticity.
    """
    if not isinstance(record, dict):
        return {"ok": False, "reason": "bad_record"}
    fields = ("venue", "market", "symbol", "tier", "before", "after", "source_id")
    if any(key not in record for key in fields):
        return {"ok": False, "reason": "missing_field"}
    if record["market"] != "usdt_perpetual":
        return {"ok": False, "reason": "market_mismatch"}
    if any(not isinstance(record[key], str) or not record[key].strip()
           for key in ("venue", "symbol", "source_id")):
        return {"ok": False, "reason": "bad_identity"}
    if not isinstance(record["tier"], int) or isinstance(record["tier"], bool) or record["tier"] < 1:
        return {"ok": False, "reason": "bad_tier"}
    if not isinstance(record["before"], dict) or not isinstance(record["after"], dict):
        return {"ok": False, "reason": "bad_transition"}
    allowed = ("max_leverage", "maintenance_margin_rate", "notional_cap")
    changed = []
    for key in allowed:
        before, after = record["before"].get(key), record["after"].get(key)
        if (before is None) != (after is None):
            return {"ok": False, "reason": "unpaired_metric"}
        if before is not None:
            try:
                b, a = _positive(before), _positive(after)
            except ValueError:
                return {"ok": False, "reason": "bad_metric"}
            if b != a:
                changed.append(key)
    if not changed:
        return {"ok": False, "reason": "no_demonstrated_change"}
    return {"ok": True, "reason": "structured_change_only", "changed_fields": sorted(changed)}
