"""K13 fail-closed tier domain and ordering checks (PAPER DATA ONLY).

This checks internally consistent manually extracted tier snapshots; it does
not establish historical availability, authenticity, or trading profitability.
"""
from decimal import Decimal, InvalidOperation


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("type")
    try:
        n = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("decimal") from exc
    if not n.is_finite() or n <= 0:
        raise ValueError("range")
    return n


def validate_tier_snapshot(tiers):
    """Return conservative verdict for ascending notional caps and risk tiers.

    Maintenance margin rates must be in (0,1), maximum leverage >=1,
    and notional caps strictly increasing. No gaps in tier numbering.
    """
    if not isinstance(tiers, list) or not tiers:
        return {"ok": False, "reason": "empty_or_invalid"}
    previous_cap = Decimal("0")
    previous_mmr = Decimal("0")
    previous_leverage = None
    for index, row in enumerate(tiers, 1):
        if not isinstance(row, dict) or set(row) != {
            "tier", "notional_cap", "maintenance_margin_rate", "max_leverage"
        }:
            return {"ok": False, "reason": "invalid_schema", "tier_index": index}
        if isinstance(row["tier"], bool) or type(row["tier"]) is not int or row["tier"] != index:
            return {"ok": False, "reason": "tier_sequence", "tier_index": index}
        try:
            cap = _number(row["notional_cap"])
            mmr = _number(row["maintenance_margin_rate"])
            leverage = _number(row["max_leverage"])
        except ValueError:
            return {"ok": False, "reason": "invalid_numeric", "tier_index": index}
        if mmr >= 1 or leverage < 1:
            return {"ok": False, "reason": "out_of_domain", "tier_index": index}
        if cap <= previous_cap or mmr < previous_mmr:
            return {"ok": False, "reason": "nonmonotonic_risk_tiers", "tier_index": index}
        if previous_leverage is not None and leverage > previous_leverage:
            return {"ok": False, "reason": "leverage_increases_with_tier", "tier_index": index}
        previous_cap, previous_mmr, previous_leverage = cap, mmr, leverage
    return {"ok": True, "reason": "internal_consistency_only"}
