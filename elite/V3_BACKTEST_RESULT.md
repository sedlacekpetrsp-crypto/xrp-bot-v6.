# ELITE V3 research decision: REJECT

GitHub Actions: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38463465534
15 unit tests passed, 105120 five-minute XRPUSDT bars evaluated.

| Segment | Trades | Win rate | Net simulated P/L (USD) | Profit factor | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Development | 702 | 34.05% | -3073.26 | 0.6705 | 31.492% |
| Validation | 173 | 30.06% | -1044.38 | 0.5695 | 11.431% |
| Holdout | 256 | 41.80% | +183.12 | 1.0416 | 8.742% |

Reject: small holdout gain does not overcome large development/validation losses.
The previously inspected holdout is no longer an untouched test for future revisions.
Do not deploy to live trading or paper as a validated profitable strategy.
