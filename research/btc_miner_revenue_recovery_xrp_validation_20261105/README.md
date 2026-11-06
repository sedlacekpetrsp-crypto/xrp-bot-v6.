# BTC_MINER_REVENUE_RECOVERY_XRP_V1 validation

Verdict: **TEST NEDOKONČEN**. The fixed historical screen passed, but no observation after the preregistration commit has yet produced independent forward PAPER evidence. This is not approved for deployment.

The source, signal, execution and gates were remotely preregistered in commit `fc9526123d5b6a820b44ea58fdd1c20e0d9309a2` before the fixed historical evaluation. Blockchain.com supplied 1,624 ordered miner-revenue observations, SHA256 `1b75573b0bdbfba5c57ea7c73ffa35d19b369a6e266cf71d61b868b46e761f72`. Although its metadata says period `day`, this `timespan=all` response contains a uniform four-day cadence. No intervening values were invented; the frozen rules explicitly operate on actual observations and all 1,623 four-day deltas are retained in `results.json`. Binance supplied 2,465 consecutive XRPUSDT daily candles through 2026-09-30 with no gaps; exact request URLs, bytes, rows and SHA256 values are retained.

Five annual-reset OOS folds contain 84 trades. Base costs produce USD 561.56 net, PF 1.5103 and USD 6.69 expectancy per trade. Doubled costs produce USD 473.40 net, PF 1.4159 and USD 5.64 expectancy. The 2022 fold loses USD 101.46 base and USD 103.18 stressed; 2023–2026 are positive at both cost levels. The frozen four-of-five stability gate therefore passes, but the negative 2022 fold remains a material limitation.

The separate continuous OOS diagnostic produces 84 trades, USD 556.94 net, PF 1.4975 and 2.40% marked drawdown at base costs; doubled costs produce USD 465.79 net, PF 1.4042 and 2.53% drawdown. The largest positive month is July 2023 at USD 172.33, 14.09% of total positive-month profit, below the frozen 25% cap. Annual folds and the continuous diagnostic reuse the same observations and must not be added as independent evidence.

The independent audit passes 6,192 checks: retained-source hashes, strict-past median and trend windows, two-observation lag, exact date alignment, next-open entries, non-overlap, risk/notional caps, fees, slippage, equity reconciliation and drawdown fields. The full repository suite passes 331 tests. Unit and audit success validate mechanics, not future profitability.

Status stays `TEST NEDOKONČEN` because the mandatory `forward_paper` gate is false. Next step: preserve these exact parameters and begin a timestamped isolated forward PAPER ledger using only miner-revenue observations and XRP candles first available after preregistration. Do not backfill that ledger, retune the 90/7/2 windows, or deploy to production. Evidence files: `results.json`, `trades.json.gz`, `audit.json`, `unit_tests.txt`.

## Forward PAPER initialization — 2026-11-06

The remotely frozen forward runner initialized at `2026-11-06T05:04:29.653Z`. The Blockchain.com response still has 1,624 observations ending 2026-10-27 and exactly matches the frozen SHA256 `1b75573b0bdbfba5c57ea7c73ffa35d19b369a6e266cf71d61b868b46e761f72`; therefore there is no new post-registration source observation. The Binance snapshot has 40 closed/warmup rows, SHA256 `d0b698b6a5033853f1b3db752f95ee177950d5a9f28198d1809be37328189dd8`; only 30 pre-forward warmup rows were frozen and zero historical bars were counted as forward trades.

The append-only ledger contains zero base and zero stressed trades and remains `COLLECTING_FORWARD_PAPER`. The quantified gate was frozen before this snapshot: at least 365 elapsed days and 20 closed trades plus positive base/stressed net and expectancy, stressed PF >1.0, stressed drawdown <=10% and single-trade concentration <=35%. The full repository suite now passes 335 tests. Next run must append only newly first-seen source observations and fully closed XRP candles; revisions or a non-prefix ledger stop the run.
