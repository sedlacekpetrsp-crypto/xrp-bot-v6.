# XRP_LEDGER_ACTIVITY_BREADTH_V1 — percentile methodology note

Saved before historical performance evaluation. The frozen 80th percentile uses
the deterministic nearest-rank definition: sort the 90 preceding breadth values
and select rank `ceil(0.80 * 90)` (one-based). The median transaction count is
the arithmetic mean of the two central sorted values. The candidate metric dated
D is excluded from both reference windows. It may be tested at the close of D+1,
and a qualifying signal enters only at the open of D+2. These definitions resolve
implementation ambiguity; no strategy parameter or acceptance gate changes.
