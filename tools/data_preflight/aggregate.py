"""Fail-closed aggregation of preflight component reports (read-only, no PnL).

Overall PASS only if EVERY required component is present and PASS.
Ordering: FAIL > UNKNOWN > PASS. A missing, malformed or unexpected-status
component is UNKNOWN (never PASS). Extra components cannot raise the status.

Input contract (dialog 0011 bod D2):
- `required` invalid (not list/tuple, empty, duplicates, non-str or empty names)
  -> ValueError. This is a caller/programming error, never a data verdict.
- `reports` and everything inside it is untrusted data: any malformed shape
  (non-dict container, non-str key, unhashable/non-str status, reason_codes not
  a list/tuple of non-empty str) yields deterministic UNKNOWN, never an exception
  and never PASS.
"""
import hashlib

from tools.data_preflight.calendar_audit import canonical_json

_RANK = {"PASS": 0, "UNKNOWN": 1, "FAIL": 2}


def _valid_codes(codes):
    return (isinstance(codes, (list, tuple))
            and all(type(c) is str and c for c in codes))


def aggregate(reports, *, required):
    if (not isinstance(required, (list, tuple)) or not required
            or not all(type(r) is str and r for r in required)
            or len(set(required)) != len(required)):
        raise ValueError("required must be a nonempty list of unique non-empty str names")
    input_codes = []
    if not isinstance(reports, dict):
        input_codes.append("REPORTS_CONTAINER_INVALID")
        reports = {}
    bad_keys = [k for k in reports if type(k) is not str or not k]
    if bad_keys:
        input_codes.append("REPORT_KEY_INVALID")
        reports = {k: v for k, v in reports.items() if k not in bad_keys}
    components, worst = {}, ("UNKNOWN" if input_codes else "PASS")
    for name in sorted(set(required) | set(reports)):
        rep = reports.get(name)
        status = rep.get("status") if isinstance(rep, dict) else None
        if name not in reports:
            status, codes = "UNKNOWN", ["COMPONENT_MISSING"]
        elif type(status) is not str or status not in _RANK:
            status, codes = "UNKNOWN", ["COMPONENT_STATUS_INVALID"]
        elif not _valid_codes(rep.get("reason_codes", [])):
            status, codes = ("FAIL" if status == "FAIL" else "UNKNOWN"), ["REASON_CODES_INVALID"]
        else:
            codes = list(rep.get("reason_codes", []))
            if status == "PASS" and codes:
                status, codes = "UNKNOWN", codes + ["PASS_WITH_REASON_CODES"]
        components[name] = dict(status=status, reason_codes=codes,
                                required=name in required)
        if _RANK[status] > _RANK[worst]:
            worst = status
    out = dict(schema_version=1, scope="preflight_aggregate_no_performance",
               status=worst, required=sorted(required), components=components,
               input_reason_codes=input_codes)
    out["report_sha256"] = hashlib.sha256(canonical_json(out).encode()).hexdigest()
    return out
