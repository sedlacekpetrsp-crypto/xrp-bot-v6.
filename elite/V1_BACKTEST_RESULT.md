# ELITE V1 — FAILED annual backtest, do not deploy

GitHub Actions run: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38462006843
Commit: 475f14e859cf50318c307018a1e2a2b26c910422
Data: 105,120 XRPUSDT 5-minute spot bars, October 2025–September 2026.
Seven unit tests passed; annual workflow succeeded technically.

| Period | Trades | Win rate | Net P/L (USD) | Profit factor | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Development | 1,449 | 42.10% | -4,224.00 | 0.7054 | 42.393% |
| Validation | 476 | 39.50% | -2,192.75 | 0.5480 | 23.227% |
| Holdout | 472 | 40.25% | -1,586.11 | 0.6855 | 17.289% |

Decision: **REJECT ELITE V1; DO NOT DEPLOY OR TRADE**.

Research caveats: simulated trades, fee/slippage assumptions, short positions
are hypothetical on spot data, and segment accounting must be reviewed before
using these as portfolio-return estimates. The negative profit factor in all
three periods is sufficient to reject this candidate regardless.

Next: independent strategy candidates, correct segment equity accounting,
cost sensitivity, and fresh out-of-sample holdout. Do not tune against the
reported holdout period and call it out of sample again.
