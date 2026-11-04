# XRP_ASIA_EUROPE_HANDOFF_REVERSAL_V1 — final validation

Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward PAPER promotion or deployment.

## Frozen mechanism and data

The remotely preregistered strategy tested whether a <=-1.50% XRP return during the complete closed 00:00–08:00 UTC Asian session mean-reverted after the 08:00 UTC European liquidity handoff. It entered at the exact 08:00 open, using only eight already closed hourly bars, past-only ATR24, a 1.5 ATR stop, 2R target and eight-hour maximum hold. There was no BTC/ETH, volume, flow, derivative, on-chain or future-price input.

Sixty-nine official Binance Vision monthly XRPUSDT spot archives from January 2021 through September 2026 supply 50,362 unique hourly candles and 369 eligible signals. `results.json` retains every exact archive URL, byte count, row count and local SHA256. Seven observed gaps totaling 14 hours were preserved; affected sessions were suppressed and no prices were fabricated. There were no duplicates.

The first unit-test command stopped before any archive download or performance output because three synthetic execution cases were placed before the required ATR24 warm-up. The fixture-only timestamp correction was documented and remotely committed before rerunning. Strategy code, real data, signal, threshold, execution and gates never changed.

## Locked OOS result

Five annual-reset OOS folds contain 280 non-overlapping trades and lose **$1,152.94**, with **PF 0.7673** and **-$4.12 expectancy** at base costs. Doubled fees and slippage lose **$2,336.29**, with **PF 0.5862** and **-$8.34 expectancy**. Base fees are $960.83 and modeled slippage $202.28; stressed fees are $1,895.71 and slippage $399.10.

Annual base PnL for 2022–2026 is -$209.94, -$178.77, -$439.93, -$86.82 and -$237.48. All five stress folds also lose. The separate continuous OOS path loses $1,104.15 base and $2,130.04 stressed, with 12.57% and 22.52% drawdown. The 2021 control loses $1,317.01 base and $1,561.05 stressed.

Only sample size passes. Net, expectancy, PF, yearly stability, final-year and drawdown gates fail at both costs. The largest positive month is only 14.44% of positive-month profit, but the frozen concentration gate cannot pass a strategy whose aggregate net is negative. There is no independent forward PAPER evidence. Reject without changing the session, threshold, direction, stop or hold.

## Verification

- `results.json`: metrics, gates, quality diagnostics and 69 source manifests.
- `trades.json.gz`: every control, annual and continuous ledger under both cost scenarios.
- `audit.json`: independent reconstruction passed 60,886 checks including 1,298 trade checks, zero failures.
- `unit_tests.txt`: all 288 repository tests passed.

Reproduce from repository root:

```bash
python -m research.run_xrp_session_handoff_reversal CACHE_DIR research/xrp_session_handoff_reversal_validation_20261104
python -m research.audit_xrp_session_handoff_reversal CACHE_DIR research/xrp_session_handoff_reversal_validation_20261104
python -m unittest discover -s tests -v
```

Hourly OHLC cannot reconstruct tick ordering, so fixed conservative ambiguity and gap rules apply. Previously inspected dates are exploratory, not untouched evidence. Passing mechanics never establish future profitability. Production, Render, LIVE, main and `v8-fly-layer-test` remain untouched.
