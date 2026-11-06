"""Read-only, bounded regular-bar calendar audit; no strategy or market imports."""
import hashlib
import json


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def audit_timestamps(timestamps, *, unit, start_ms, end_ms, interval_ms):
    """Audit bar opens against an externally declared UTC [start, end) grid.

    PASS applies only to timestamp coverage, never prices, PIT availability or
    strategy eligibility. Unknown units are not inferred from magnitudes.
    No sorting, deduplication, imputation or interval trimming repairs the input.
    Missing timestamps are counted arithmetically without allocating the grid.
    """
    if any(type(x) is not int for x in (start_ms, end_ms, interval_ms)):
        raise ValueError("calendar bounds and interval must be integer milliseconds")
    if interval_ms <= 0 or end_ms <= start_ms or (end_ms-start_ms) % interval_ms:
        raise ValueError("require a nonempty whole-bar half-open calendar")
    raw = list(timestamps)
    if any(type(x) is not int for x in raw):
        raise ValueError("timestamps must be integers, not floats, strings or bools")
    evidence = dict(timestamps=raw, unit=unit, start_ms=start_ms,
                    end_ms=end_ms, interval_ms=interval_ms)
    report = dict(schema_version=1, scope="regular_bar_timestamp_coverage_only",
                  input_sha256=hashlib.sha256(canonical_json(evidence).encode()).hexdigest(),
                  calendar=dict(start_ms=start_ms, end_ms=end_ms, interval_ms=interval_ms),
                  row_count=len(raw), reason_codes=[])
    if unit not in ("ms", "us"):
        report.update(status="UNKNOWN", reason_codes=["TIMESTAMP_UNIT_UNKNOWN"])
        return report
    factor = 1 if unit == "ms" else 1000
    start, end, step = start_ms*factor, end_ms*factor, interval_ms*factor
    unique = set(raw)
    duplicate = len(raw)-len(unique)
    decreases = sum(a > b for a, b in zip(raw, raw[1:]))
    outside = sum(not start <= t < end for t in raw)
    off_grid = sum((t-start) % step != 0 for t in raw)
    present = sum(start <= t < end and (t-start) % step == 0 for t in unique)
    expected = (end-start)//step
    counts = dict(duplicate_rows=duplicate, decreasing_pairs=decreases,
                  outside_rows=outside, off_grid_rows=off_grid,
                  expected_bars=expected, covered_bars=present,
                  missing_bars=expected-present)
    codes = [code for count, code in (
        (duplicate, "DUPLICATE_TIMESTAMP"), (decreases, "NON_MONOTONIC_TIMESTAMP"),
        (outside, "OUTSIDE_CALENDAR"), (off_grid, "OFF_GRID_TIMESTAMP"),
        (expected-present, "MISSING_BARS")) if count]
    report.update(status="FAIL" if codes else "PASS", reason_codes=codes, counts=counts)
    return report
