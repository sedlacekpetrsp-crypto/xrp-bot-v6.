# Frozen V15–V17 portfolio routing experiment — 2026-10-14

Research only, same isolated branch. No Render/app changes or orders.
Hypothesis: deterministic routing of distinct entry families may improve regime
coverage versus isolated strategies. These combinations were selected after
seeing component results, so all 2023–2026 data remain DEVELOPMENT, not OOS.
No adding independently simulated profits or giving each strategy its own
10,000 account. One shared cash ledger, one position, 0.5% planned risk and
35% maximum allocation. Entry priority is fixed in advance, never by future P/L.

- V15: first available entry in priority V8 shock, V10 pullback, V5 breakout.
- V16: hourly regime gate: price above 168-hour SMA and 72-hour efficiency
  ratio >0.20 permits V5 breakout entries; otherwise only V8 shock entries.
  Regime calculated only from completed hourly candles. Threshold is fixed
  for this batch; no sweep over thresholds. No minimum rising-SMA requirement.
- V17: first available entry in priority V8 shock, V10 pullback, V11 filtered
  breakout. Different from V15 only in the breakout family, acknowledged.

While a position is open, only its owning component's exit decisions apply.
Other entries and exit signals cannot replace, close or resize that position.
No averaging down, portfolio leverage, simultaneous trades or modified stops.
When flat and multiple entries arrive, choose the first eligible component.
On exit at open, no reentry on that same bar, consistent with existing engine.

Execution/costs, chronological development blocks, continuous account, bootstrap,
benchmarks and acceptance gates remain exactly as in PROTOCOL_V8_V11.md:
>=3/4 profitable blocks; continuous >=60 trades, PF>=1.2, close DD<=10%,
intrabar bound<=12%, positive doubled-cost P/L, positive 95% lower daily-P/L
bootstrap bound (7-day blocks, 2000 draws, seed713).
All variants and losers reported. Analysis of overlap/ownership and winner
concentration is diagnostic, not a changed acceptance threshold.

Only discovery survivors may open reserved 2022 historical challenge. 2021
stays reserved. No PAPER approval on development results, even if a router
passes. Future prospective validation is still necessary; backward testing
is not forward OOS. No trading with real money without explicit approval.
