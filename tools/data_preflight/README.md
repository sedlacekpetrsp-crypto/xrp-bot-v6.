# Calendar audit component (PAPER research, H-C2)

Isolated proposal for Claude's shared preflight. Based on dialog commit
`bc5957ca875257f0286460a2ab14e97049e8a708`; no integration into any runner.

`audit_timestamps` checks regular bar opens against an explicitly supplied UTC
millisecond calendar `[start_ms, end_ms)`. Call once per instrument/stream.
The start is the grid anchor and must come from the predeclared protocol, never
from min/max observed timestamps. Units are explicitly `ms` or `us`; unknown
units return UNKNOWN. Invalid numeric types or invalid calendars raise ValueError;
callers must treat these exceptions as blocking, never PASS.

PASS means timestamp coverage ONLY. It says nothing about OHLC values, source
authenticity, listing history, point-in-time availability, execution or profit.
FAIL does not determine whether a gap is an outage, missing publication or
delisting. No gaps are filled or labelled market_closed. No intervals are trimmed.
Do not use this regular-bar grid for variable funding settlement schedules.

The input fingerprint hashes canonical JSON of the ordered timestamp list,
explicit unit and calendar; it is NOT a raw archive SHA-256. Claude's manifest
must separately hash exact source bytes and record provenance. Runtime/memory
are O(input rows), not O(expected bars); the current implementation is in-memory.

Example (synthetic):

```python
from tools.data_preflight.calendar_audit import audit_timestamps
report = audit_timestamps([0, 60000, 60000], unit="ms", start_ms=0,
                          end_ms=180000, interval_ms=60000)
# FAIL: DUPLICATE_TIMESTAMP, MISSING_BARS; one missing, one duplicate.
```

Validation actually executed in Work on 2026-11-06:

```
python -m unittest discover -s tests -p test_preflight_calendar.py -v
Ran 15 tests in 0.001s — OK
```

All fixtures are synthetic. No market download or performance run occurred.
Remaining H-C2 work: raw-file manifest, parsers, OHLC/cross-archive conflicts,
funding/PIT availability, full report aggregation and independent review.
No workflows added; OWNER_DECISIONS and frozen runners remain unchanged.
