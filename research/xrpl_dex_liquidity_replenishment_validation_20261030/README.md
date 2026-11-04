# XRPL_DEX_LIQUIDITY_REPLENISHMENT_V1 — final validation

Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no deployment or forward PAPER promotion.

## Frozen hypothesis and data

The protocol was committed before performance evaluation. It tested whether growth in absolute, explicitly funded two-sided XRP/GateHub USD depth within 2% of the native XRPL DEX mid preceded positive XRP spot expectancy. It did not use order-book imbalance, price direction, relative strength or any previously rejected strategy family.

The immutable ledger sequence was 60,000,000 through 107,400,000 at a fixed 120,000-ledger stride. The 2026-10-01 cutoff retained 395 snapshots through ledger 107,280,000. Every retained RPC response in `results.json` includes its exact request, byte count, ledger hash, cache filename and local SHA256. Of the 395 retained snapshots, 303 were valid and 92 were excluded under the frozen missing/crossed/spread/truncation rules; no price or book was imputed. Binance XRPUSDT daily execution data contain 2,099 consecutive rows from 2021-01-01 through 2026-09-30 without detected gaps.

The public XRPL node repeatedly returned `tooBusy`. Two pre-performance operational amendments changed downloader concurrency only (8 to 16, then 16 to 4); both were committed before any performance output. Endpoint, ledgers, payloads, parsing, signals, execution and gates were unchanged. A completed cache was not treated as a result until all 396 requested ledger points had their original response files.

## Locked OOS result

Annual-reset OOS folds are 2022, 2023, 2024, 2025 and 2026 through September. The 115 non-overlapping base-cost trades lost **$163.66**, with **PF 0.9048**, **-$1.42 expectancy**, $104.93 fees and $22.09 modeled slippage. The same trades under doubled costs lost **$287.95**, with **PF 0.8388**, **-$2.50 expectancy**, $209.61 fees and $44.13 modeled slippage.

Annual base net PnL was +$39.47, +$25.30, -$232.50, +$159.18 and -$155.12 for 2022–2026. Stress PnL was +$12.00, -$6.63, -$260.00, +$142.13 and -$175.45. Only two of five years were positive at both cost levels and final 2026 lost. The separate continuous OOS path lost $119.57 base and $245.07 stressed, with 3.63% and 4.05% maximum drawdown. Positive-month profit concentration was 18.21%, but its gate cannot pass when aggregate PnL is negative.

The frozen sample and drawdown gates passed. Base/stress net, expectancy, PF, yearly stability, final-year and concentration gates failed. There is no independent forward PAPER evidence. The candidate is rejected without tuning, inversion, issuer substitution or selection of profitable years.

## Verification and artifacts

- `results.json`: full metrics, gates and complete source manifests with URLs and SHA256.
- `observations.json.gz`: all derived XRPL observations, including invalid snapshots as null.
- `trades.json.gz`: every fold and cost-scenario trade ledger.
- `audit.json`: independent reconstruction passed 5,176 checks, including 498 trade checks, with zero failures.
- `unit_tests.txt`: 268 repository tests passed.

Reproduce from repository root with:

```bash
python -m research.run_xrpl_dex_liquidity_replenishment CACHE_DIR research/xrpl_dex_liquidity_replenishment_validation_20261030
python -m research.audit_xrpl_dex_liquidity_replenishment CACHE_DIR research/xrpl_dex_liquidity_replenishment_validation_20261030
python -m unittest discover -s tests -v
```

The cache is intentionally not committed because it contains large raw RPC responses; the retained manifest makes every response independently identifiable. Public full-history availability, GateHub USD issuer credit, venue specificity and daily-OHLC path limits remain permanent limitations.

Next step: close this native-DEX liquidity family and perform a source-coverage feasibility check for a genuinely different, timestamped XRP payment-channel or escrow-utilization mechanism. Preregister it only if complete historical ledger objects can be reproduced without imputation or paid data. Production, Render, LIVE, main and `v8-fly-layer-test` remain untouched.
