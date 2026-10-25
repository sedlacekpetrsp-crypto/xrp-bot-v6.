# XRP_FUNDING_DISLOCATION_REVERSAL_V1 — frozen protocol (2026-10-25)

Status: **REGISTERED; NOT EVALUATED.** This is a new observable mechanism: periodic perpetual-futures funding, not OI/account ratios, taker-flow pressure, spot volume/trade size, calendar drift, autocorrelation, cross-asset momentum/residuals, stablecoin parity or triangular parity. Hypothesis: an unusually negative XRP perpetual funding payment reflects temporary short-side demand; after the payment, spot XRP has positive 12-hour rebound expectancy.

Data: Binance Vision XRPUSDT USD-M monthly `fundingRate` plus XRPUSDT spot monthly 1h klines, January 2022–September 2026. Each archive URL, byte count and locally computed SHA256 must be recorded. Sort and reject duplicate/non-hour timestamps. Preserve and report gaps; never impute. Funding history is valid only when each adjacent timestamp equals the preceding record's published `funding_interval_hours`.

Fixed causal rule: after a completed funding record, its `last_funding_rate` must be negative and at or below the empirical 10th percentile of the preceding 90 funding records (current excluded). Enter spot long at the next hourly open. ATR24 from fully closed contiguous hourly bars; stop 1.5 ATR, target 2R, maximum hold 12 bars. Stop wins same-bar ambiguity; a gap through stop fills at the worse opening price. Fee 9.5 bps/side plus adverse slippage 2 bps/side; stress doubles both. Risk 0.5% equity, notional <=20%, one non-overlapping position, no leverage. Spot execution means no funding cashflow is claimed.

2022 is control. Locked OOS quarters are 2023 Q1 through 2026 Q3; the continuous OOS path is non-independent. All historical gates: >=150 OOS trades; positive base net/expectancy and PF>1.15; positive stress net/expectancy and PF>1.02; >=10/15 positive quarters including 2026 Q3; continuous base and stress drawdown <=10%; no quarter contributes >30% of total positive OOS profit. Historical passage remains `TEST NEDOKONCEN` until >=30 future days and >=100 new PAPER trades have positive stressed expectancy. No threshold tuning after results and no LIVE, production, Render, main or deployed-branch changes.

Next: commit this protocol, implementation and deterministic tests before downloading or evaluating historical outcomes.

## Pre-results timestamp amendment

Initial ingestion stopped in `validate` before any trade or performance calculation because Binance funding `calc_time` values are sometimes a few milliseconds after the nominal hour (observed offsets 1–31 ms). Funding timestamps within 1,000 ms of an exact hour will be normalized to that hour solely for causal alignment to the next spot-hour open; each archive records the count and maximum absolute adjustment. A larger offset is rejected. Rates, prices, signal thresholds, execution rules and gates are unchanged; no price or missing observation is synthesized.

## Completed historical validation — rejected

The amended protocol was hashed before evaluation (`cd71e15f6fc64836894ef4f6bfe811cc92d5bb3b0caa1d56d90693f5c29053a5`). The completed run used 57 Binance funding archives and 57 Binance spot 1h archives. `results.json` records every source URL, byte count and local SHA256. It normalized 2,221 publisher timestamps by 1–31 ms as preregistered, found no duplicates or unexpected funding gaps, and retained one real missing spot hour between 2023-03-24 12:00 and 14:00 UTC. No position or candidate signal crossed that gap; nothing was imputed.

The 15 locked OOS quarters produced 321 base-cost trades, -$1,403.59 net, PF 0.7585 and expectancy -$4.37. Doubled costs produced the same 321 signals and lost $2,754.20, PF 0.5855 and expectancy -$8.58. Only four quarters were base-cost positive; final 2026 Q3 lost $207.77. The continuous, non-independent OOS path lost $1,328.22 with 15.26% maximum drawdown; stress lost $2,439.18 with 25.26% drawdown. Only the sample-size gate passed; every profitability, stress, stability, final-quarter, drawdown and concentration gate failed. The 2022 control also lost.

All 58 repository unit tests passed. `audit_funding_reversal.py` independently reconciled causal timing, thresholds, non-overlap, holding time, sizing, costs, slippage, P/L and equity for every ledger and wrote a PASS audit. Mechanics correctness is not profitability evidence. Reject without retuning and do not open a forward PAPER stage.

Next concrete step: stop testing derivatives-crowding variants on these periods. Preregister a distinct mechanism using a new observable data family and reserve fresh forward observations before acceptance. Keep production, Render, LIVE, main and deployed branches untouched.
