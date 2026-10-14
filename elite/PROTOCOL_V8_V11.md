# ELITE V8–V11: frozen batch, 2026-10-14

No deployment. No existing bot changes. This protocol is frozen before new
candidate results. Four candidates only; no parameter grid and no changing
thresholds after observing this batch. All are spot LONG-only without leverage.

## Hypotheses
- V8 / shock recovery: 4h return below -2.5 times trailing 30-bar return standard
  deviation, followed by a positive 4h close above the shock bar's midpoint.
  ATR(14)*2 stop, reward/risk 2, maximum 48h. No trend requirement. Baseline
  volatility excludes the shock and confirming bar.
- V9 / range reversion: hourly close below trailing 48-hour mean minus 2.5 SD,
  efficiency ratio over 48 hours below 0.25, close above previous close (rebound).
  Stop 2 ATR, target 3 ATR, exit at prior 48-hour mean, maximum 24h.
- V10 / trend pullback: 4h close above 120-bar SMA with the SMA rising over 6 bars;
  prior low touches the prior 20-bar SMA and current close crosses back above
  current 20-bar SMA. Stop 3 ATR; exit below 60-bar SMA; maximum 7 days.
- V11 / efficient trend: hourly 72-bar high breakout, 72-hour efficiency >0.35,
  price above 168-hour SMA and that SMA rising over 24 hours. Stop 4 ATR;
  exit below 24-hour low. No timeout. This is explicitly a filtered V5 descendant,
  not an unrelated strategy; every prior V5 result is part of its development.

## Discovery and data lock
All April 2023–September 2026 data are now DEVELOPMENT, including previously
named holdouts. Evaluate four fixed blocks: Apr–Dec 2023; H1 2024; H2 2024;
Jan 2025–Sep 2026. Report every candidate, all blocks, a continuous run,
quarterly P/L, stress costs, ledger, uncertainty and buy/hold baselines.
Discovery gate: positive net P/L in at least 3/4 blocks; aggregate continuous
PF >=1.2, at least 60 trades, close MTM DD <=10%, intrabar bound <=12%, positive
continuous stress net P/L and positive 95% bootstrap lower mean-daily-P/L bound.
These are screening gates, not PAPER eligibility. No lowering gates afterward.

Only candidates passing discovery may unlock 2022 historical challenge data;
2021 remains reserved. 2022 was not inspected in this session. Historical
challenge is backward testing, NOT genuine forward walk-forward OOS because
hypotheses were developed using later years. Evaluate 2022 H1 and H2 separately:
net and stress net positive in both, PF >=1.2 in both, >=30 combined trades,
close DD <=10%, intrabar bound <=12%, positive continuous bootstrap lower bound.
No candidate passing discovery means challenge stays unopened. A historical
challenge pass still requires new prospective data and PAPER observation before
claiming robustness. Do not reuse historical challenge for another fit after
inspection. Do not claim that earlier unseen user work never used these years.

## Execution and evidence
Unchanged audited research engine: next 5m open execution, one position,
0.5% planned risk inclusive of costs, maximum 35% allocation, 10,000 USDT start.
Fee/slippage/half-spread per side = .001/.0003/.0001; stress doubles all.
Compare cash (0 return) and buy/hold with 35% and 100% allocation including
same transaction costs. Benchmarks are context, not adjusted-risk equivalents.
Use 7-day block bootstrap, 2000 replicates and seed 713. Report 2024 Q4 profit
concentration; no interpretation of one favourable quarter as a durable edge.
Save source and complete evidence on elite-research-v1. No real orders or APIs.
