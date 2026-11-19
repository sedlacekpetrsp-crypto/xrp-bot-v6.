"""K9 data-only audit: reject ambiguous or duplicate month records before network reads.

Standalone diagnostic; not wired into performance runner pending independent review.
"""
from __future__ import annotations

import re

_MONTH = re.compile(r"^(20[0-9]{2})-(0[1-9]|1[0-2])$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def validate_manifest_months(manifest: dict) -> dict:
    """Fail closed on duplicate asset/month, malformed provenance or missing records."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("months"), list):
        raise ValueError("months must be a list")
    seen = set()
    ok = 0
    for pos, rec in enumerate(manifest["months"]):
        if not isinstance(rec, dict):
            raise ValueError(f"month record {pos} must be an object")
        asset, month, status = rec.get("symbol"), rec.get("month"), rec.get("status")
        if not isinstance(asset, str) or not re.fullmatch(r"[A-Z0-9]{3,20}", asset):
            raise ValueError(f"invalid symbol at {pos}")
        if not isinstance(month, str) or not _MONTH.fullmatch(month):
            raise ValueError(f"invalid month at {pos}")
        key = (asset, month)
        if key in seen:
            raise ValueError(f"duplicate asset/month: {asset} {month}")
        seen.add(key)
        if status == "OK":
            sha = rec.get("sha256")
            if not isinstance(sha, str) or not _SHA.fullmatch(sha):
                raise ValueError(f"missing or invalid SHA-256: {asset} {month}")
            ok += 1
        elif status not in ("MISSING", "INVALID", "EXCLUDED"):
            raise ValueError(f"unrecognized status: {asset} {month}")
    if not seen or ok == 0:
        raise ValueError("no eligible months")
    return {"unique_months": len(seen), "eligible_months": ok, "diagnostic_only": True}
