# ELITE V2 — annual research backtest: REJECT

GitHub Actions run: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38462995260
Data: 105,120 5m XRPUSDT spot candles, October 2025–September 2026.
All 11 unit tests passed; historical evaluation completed successfully.

| Period | Trades | Win rate | Simulated P/L USD | Profit factor | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Development | 403 | 34.49% | -1700.74 | 0.5865 | 17.007% |
| Validation | 108 | 34.26% | -575.86 | 0.4564 | 6.079% |
| Holdout | 121 | 26.45% | -821.21 | 0.3725 | 8.212% |

Decision: **REJECT V2**. No paper/live deployment.
Note: simulated short fills on spot candles are not executable spot shorts.
Period P/L and drawdown calculations need independent review before portfolio claims.
Both V1 and V2 are rejected. Do not retune on the previously exposed holdout and
call it an independent test. New candidate research must use a new forward holdout.
