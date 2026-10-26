# XRP_ATTENTION_SHARE_SURGE_V1 — completed validation

Decision: **NEPROŠEL**. The protocol, code and gates were frozen in GitHub commit `a9b4c46350b4e88401646e1bb57608778d22f3f3` before performance evaluation.

The run used 285 real Binance Vision monthly spot archives for BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT and XRPUSDT, January 2022–September 2026. Each market supplied 41,615 hourly bars, with no duplicates or cross-market omissions. The one exchange-wide missing hour on 2023-03-24 was preserved; every 181-day window crossing it was suppressed. URLs, byte counts and locally computed SHA256 fingerprints are in `results.json`.

Across four annual OOS folds, 172 non-overlapping base-cost trades lost **$964.12**, PF **0.7981**, expectancy **-$5.61/trade**. Doubled fees/slippage lost **$1,570.53**, PF **0.6926**, expectancy **-$9.13/trade**. Every OOS year lost. Continuous OOS drawdown was 12.74% base and 17.18% stressed. The 2022 control also lost. Only the frozen sample-size gate passed.

All 89 repository tests passed. An independent audit importing no strategy code passed 5,082 checks covering next-open timing, non-overlap, fees, P/L, sizing and equity reconciliation. Complete metrics/provenance are in `results.json`, ledgers in `trades.json.gz`, and audit evidence in `audit.json`. Mechanics success is not profitability evidence.

Do not retune the 80th percentile or basket on these observed years, and do not promote to forward PAPER. Next concrete step: preregister a mechanism outside cross-market attention/volume allocation and preserve future observations for any candidate that passes historical gates.

