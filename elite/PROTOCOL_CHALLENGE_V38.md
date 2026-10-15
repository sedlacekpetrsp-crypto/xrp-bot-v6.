# Reserved2022 challenge for frozen V38 — 2026-10-15

V38 passed all unchanged discovery gates; V39 failed and is NOT tested here.
First inspection of2022 in this series. Use exact strategy/engine code hashes
from saved discovery report; abort if changed. Existing challenge gates in
PROTOCOL_V8_V11.md apply, not thresholds fitted to2022 outcomes.

Full Jan–Dec2022 XRP/BTC checked monthly data, no2021 warmup (2021 remains
reserved); initial200 hourly bars without entries. No date exclusion,fill or
interpolation for gaps: fail closed and report data block. No2022 data were
opened before this protocol. Signals may use earlier2022 history for H2;
accounts/overlay state reset at each half. Continuous full-year run also.
No changes to7day pause,3-loss streak,V18 entries,position size,costs or gates.
V38's strict-stream argument is empty because its fixed branch never uses it;
V39/taker-flow data are not evaluated in this challenge.

Acceptance from original protocol: BOTH halves base and stress net P/L>0,
BOTH base PF>=1.2,>=30 combined half-year trades,closeDD<=10%,intrabar bound<=12%
in both halves and continuous; positive continuous95% lower bootstrap daily
mean. Costs and bootstrap as discovery. Retain every ledger,event and manifest.
This is BACKWARD historical challenge, not prospective validation. Record2022
as consumed after inspection; do not fit another candidate to this challenge
and call it independent.2021 remains reserved. Failure means no PAPER; a pass
still needs prospective validation/PAPER observation and is not LIVE approval.
No existing bot or deployment changes.
