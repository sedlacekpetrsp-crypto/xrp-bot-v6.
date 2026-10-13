# Frozen protocol — 2026-10-13

This protocol is committed before downloading/evaluating the new candidates.
V4 is rejected: original annual run 38464412943 on source 7056783, 105120 bars,
net P/L development -1242.88, validation -594.84, reused holdout -198.77 USD.
Each split starts at 10000. Do not add split P/L and call it compounded annual P/L.
Original drawdown only measures closed trades. The V4 48/96-bar means are 4/8
hours, not multi-day; inherited 24-bar timeout is 2 hours. Prior V1–V4 use of
2025-10 through 2026-09 means that year is now diagnostic, NOT a fresh holdout.

## Fixed hypotheses (spot LONG only; no grid search)
- V5: hourly 72-bar Donchian breakout, 24-bar channel exit, 3 ATR stop.
- V6: four-hour 20/60 SMA positive trend crossover; exit when fast <= slow;
  3 ATR stop. Designed to retain trends without a two-hour forced timeout.
- V7: hourly two-period RSI < 10 above 200 SMA; exit RSI > 60, 2 ATR stop,
  maximum 24 hours. A pullback hypothesis distinct from channel breakout.
Only completed aggregate bars produce signals, executed at next 5m open.
One position; 0.5% planned equity risk; 35% maximum allocation; no leverage.

## Data and partitions
Binance Vision checksummed XRPUSDT 5m spot OHLC, 2023-01 through 2026-09.
Development 2023; validation 2024 H1; historical holdout 2024 H2; diagnostic
2025-01 through 2026-09. These earlier years are newly evaluated in this study,
not a claim that no earlier researcher ever inspected them. Historical results
cannot replace prospective paper validation. Indicators may warm up on earlier
bars, but trades cannot cross split boundaries. Each split resets to 10000.
If any tuning occurs after looking at results, these periods become development.

## Execution and predeclared screening gates
Baseline per side: fee 0.10%, adverse slippage 0.03%, half-spread 0.01%.
Stress: double all three. Fees are assumptions, not a verified account tariff.
Stop gaps fill at worse open; simultaneous stop/target uses stop first.
Track liquidation-valued close equity and conservative intrabar drawdown bound.
Acceptance per validation and holdout: >=30 trades, net profit >0, PF >=1.2,
close MTM drawdown <=10%, intrabar bound <=12%, and positive stress net profit.
Development must also be profitable. Report quarterly stability and daily-block
bootstrap confidence intervals (7-day blocks, 2000 draws, fixed seed). Require
positive 95% lower bound on mean daily P/L in validation AND holdout; this is a
screening statistic, not proof, and does not remove multiple-comparison bias.
Report all candidates, even rejected ones. No selecting solely on aggregate P/L.
No candidate passing all gates => no PAPER deployment. Stop this experiment
batch with an honest rejection report, rather than tuning until history is green.

## Safety
No existing app, Render config, bot branch, live credentials, or order endpoints
may be changed. Research code and results only on elite-research-v1. No deploy.
A passing candidate still needs prospective PAPER observation before any live
proposal; live trading always requires explicit user approval.
