# XRP_AGGRESSOR_SELL_BURST_REVERSAL_V1 — exact-duplicate amendment

Recorded and committed before any performance result was produced.

The run using the previously registered full-file ordering correction stopped again before bar completion or backtesting. After numerical ID sorting, the affected February 2026 archive contains 4,000 adjacent duplicate aggregate-trade IDs. An independent full-file comparison found all 4,000 duplicate pairs to be byte-for-byte identical across every CSV field, with zero conflicting pairs and zero timestamp reversals in the sorted file.

Frozen ingestion-only correction: after sorting the exact previously identified archive SHA, collapse only a repeated row whose aggregate-trade ID and complete CSV row are identical to the immediately preceding row. Count and report every removed exact duplicate. Any repeated ID with a different field, any remaining non-increasing ID, or any timestamp reversal must stop the run before evaluation. Other archives remain untouched. The no-imputation and invalid-adjacent-minute rules remain unchanged.

This removes duplicated publisher records without inventing or changing prices, sides, quantities, or timestamps. Strategy rules, costs, folds, and acceptance gates are unchanged. No trade return or performance metric existed when this amendment was written.
