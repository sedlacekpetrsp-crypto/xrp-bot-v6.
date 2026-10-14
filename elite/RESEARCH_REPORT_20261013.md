# ELITE: V4 audit and V5–V7 frozen experiment

**Decision: no candidate qualifies for PAPER deployment. No deployment performed.**

## Scope and evidence

Only the `elite-research-v1` research branch was changed. Existing app files,
Render settings, other bot branches and live execution were untouched.
Protocol was committed as `71729de` before new candidate evaluation; engine and
pre-result data-coverage amendment as `258bb0e`. Reproducible runner/CI source:
`162b5cf`. Full numerical results are in `results/20261013/summary.json`;
checksums and source URLs in `data_manifest.json`; all base/stress trade ledgers
and daily equity curves in `evidence.tar.gz`.

## V4 completed and rejected

Original GitHub run: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38464412943
Source: `7056783`. Local reproduction matched all original reported split values.
105,120 5m candles, October 2025–September 2026; each split starts at 10,000 USDT.

| Original split | Trades | Net USDT | Profit factor | Closed-trade DD |
|---|---:|---:|---:|---:|
| Development | 228 | -1242.88 | 0.6456 | 13.110% |
| Validation | 70 | -594.84 | 0.4702 | 6.997% |
| Previously reused holdout | 70 | -198.77 | 0.8224 | 3.851% |

The original simulator included 0.05% fees and 0.02% slippage per side.
210 of 368 exits were TIME, 140 STOP, and 18 TARGET. The claimed slow trend used
48/96 five-minute bars (4/8 hours), with a maximum two-hour holding period.
With fees and slippage disabled, development still lost 238.12 USDT and validation
256.87 USDT; only the reused holdout gained 115.98 USDT. Thus costs matter, but
there is no demonstrated gross edge across periods either.

The new simulator records liquidation-valued close equity and a conservative
intrabar drawdown bound, includes costs in planned risk sizing, and supports
higher-timeframe signal exits at the next 5m open. V4 on this engine is a separate
audit, not an exact replication: risk sizing and timeout fill convention differ.
Both implementations reject V4. The original implementation remains unchanged
so the old result is reproducible. `v4_audit.json` contains both sets of metrics.

## New experiment

42 complete, checksummed months: April 2023–September 2026, **368,352 candles**.
The initial strict data check found 16 missing candles in March 2023; the protocol
was amended before candidate results to start in April, without imputing prices.
Development: April–December 2023. Validation: January–June 2024. Historical
holdout: July–December 2024. Diagnostic: January 2025–September 2026.
The final diagnostic interval overlaps prior research and is not untouched OOS.
All inspected periods are now consumed for future model selection.

Three fixed spot LONG-only hypotheses, no grid search:

- **V5:** hourly 72-bar channel breakout, 24-bar channel exit, 3 ATR stop.
- **V6:** four-hour 20/60 SMA crossover, reverse-cross exit, 3 ATR stop.
- **V7:** hourly two-period RSI pullback above 200 SMA, RSI recovery exit,
  2 ATR stop and maximum 24 hours. RSI here uses the two simple bar changes,
  not Wilder smoothing.

Each split starts with 10,000 USDT, at most one position, no leverage, 35%
maximum allocation and 0.5% planned risk including transaction costs. Baseline
per side: 0.10% fee, 0.03% slippage and 0.01% half-spread; stress doubles all.
These are declared assumptions, not a claim about the user's exchange tariff.
Indicators use closed bars only; entries and signal exits occur at the next 5m
open. Gap stops use the worse open. A simultaneous stop/target assumes stop first.
Positions are liquidated at split boundaries; no trades carry into a new split.

| Candidate | Development net | Validation net | Holdout net | Diagnostic net |
|---|---:|---:|---:|---:|
| V5 | -184.84 | -583.38 | +3708.86 | +2534.85 |
| V6 | +385.56 | -397.88 | +2226.64 | +76.23 |
| V7 | -1730.65 | -2063.01 | -923.61 | -4163.18 |

Amounts are USDT **after costs**; columns are independently reset accounts, not
additive annual returns. Positive holdout results alone do not qualify a strategy.

| Candidate / period | Trades | PF | Close MTM DD | Intrabar DD bound | Stress net |
|---|---:|---:|---:|---:|---:|
| V5 validation | 23 | 0.176 | 6.70% | 6.71% | -630.94 |
| V5 holdout | 25 | 4.804 | 8.83% | 8.88% | +3260.99 |
| V6 validation | 13 | 0.112 | 4.84% | 4.85% | -410.08 |
| V6 holdout | 9 | 8.741 | 9.24% | 9.87% | +2132.87 |
| V7 validation | 249 | 0.309 | 20.75% | 20.77% | -3167.65 |
| V7 holdout | 326 | 0.688 | 10.03% | 10.06% | -2172.26 |

### Why none passes

V5 and V6 fail validation and the predeclared minimum of 30 trades in both
validation and holdout. About 93% of each strategy's holdout profit arose in
2024 Q4: strong dependence on one favourable quarter. Seven-day block bootstrap
(2,000 draws, fixed seed) has a nonpositive 95% lower mean-daily-P/L bound in
both validation and holdout for every candidate. This statistic is a screening
tool, not a multiple-testing-adjusted profitability guarantee.

V7 loses in every split and incurs substantial turnover costs. Its validation
close-equity drawdown is 20.75%, versus the 10% gate. V6's diagnostic gain falls
to -4.12 USDT under doubled costs. V5's diagnostic profit is encouraging only
as exploratory evidence; it cannot erase development/validation failure.

## Verification and limits

28 local unit tests pass, including exact fee accounting, gap stops, stop/target
ordering, next-open entries/exits, open-position drawdowns, incomplete aggregate
bars, split isolation, invalid data and prefix invariance under future changes.
GitHub CI passed all 28 tests and repeated the frozen V5–V7 experiment; all
printed split P/L, trade counts and rejection gates matched the local run.
GitHub Actions: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38465472597
A green workflow means the experiment ran, not that strategies passed.

OHLC cannot recover the actual intrabar path. The intrabar DD is deliberately
pessimistic; stop fill and constant slippage are models, not observed executions.
No queue position, order book depth or liquidity-dependent impact is modeled.
Spot LONG-only testing avoids pretending that spot shorts can be executed.
No funding model is applicable here. Historical holdout results do not substitute
for future data or a prospective PAPER record.

## PAPER decision and next research boundary

`paper_eligible` is empty. Do not deploy these candidates as validated strategies.
No order-capable paper/live adapter or Render service was created. A future
passing candidate would require an isolated PAPER-only process with no trading
credentials, persistent ledger, stale-data guard, restart reconciliation,
loss limits and a prospective observation period before any live proposal.
Live trading requires separate explicit user approval.

This batch ends with rejection rather than changing thresholds until results
turn green. Any further strategy changes must label these historical periods
as development and reserve genuinely unused data/prospective observations.
V5 is a research lead, not a selected or approved trading strategy.

## Reproduce

```bash
python -m unittest discover -s elite -p 'test_*.py' -v
python -m elite.research_run --cache /tmp/elite-data --out /tmp/elite-results
python -m elite.data_loader --start 2025-10 --end 2026-09 --out /tmp/xrp-v4.csv
python -m elite.audit_v4 --csv /tmp/xrp-v4.csv --output /tmp/v4-audit.json
```
