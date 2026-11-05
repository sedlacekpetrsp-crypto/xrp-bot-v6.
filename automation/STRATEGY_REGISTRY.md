# Registr strategií (PAPER) — vede autopilot

Založeno 2026-11-05 10:05 UTC. Zdroj historické části: `reports/hypothesis-inventory-20261105.{md,json}`
(110 hypotéz), metriky po nákladech: `reports/strategy-review-20261105.md` (oddíl B) a soubory níže.
**Žádná strategie nemá nezávisle validovaný zisk po nákladech.** Stavy: zamítnuto / ve validaci / forward PAPER.

## A. Strategie běžící v produkci (forward PAPER)

Data: živé PAPER účty na Renderu (`srv-dang770ae00c73em1sm0`), obchody v PostgreSQL (`*_trades`),
P/L po poplatcích a skluzu tak, jak je počítá bot. Snapshot 2026-11-05 09:59 UTC (run 42006901448).

| Strategie | Větev / kód | Tabulka obchodů | Obchodů | Net USDT | Stav |
|---|---|---|---|---|---|
| FLY | v8-fly-layer-test / app_v8_fly | v8fixed_trades (+ fly_trade_exclusions) | 287 | −821,80 | pauza; forward PAPER zastaven |
| FAST | v8-fly-layer-test | fast_scalp_trades | 104 | −413,46 | pauza |
| TV Consensus | v8-fly-layer-test | tv_consensus_trades | 112 | −436,87 | pauza; 9 variant ztrátových |
| LEADLAG | v8-fly-layer-test | leadlag_trades | 8 | −50,44 | pauza |
| WHALE (FIB / VWAP reclaim / trendline 4h 0,1 %) | v8-fly-layer-test (PR #7) | blue_whale_trades | 9 | −718,29 | forward PAPER |
| BEST-OF (BREAKOUT, FIB, EMA 4h) | v8-fly-layer-test / app_bestof_core | bestof_trades | 129 (z toho 1 duplikát id 129) | −383,00 (zůstatek) | forward PAPER; varianty neprošly; PR #8 (duplicitní zápis) |
| LH-WHALE | v8-fly-layer-test / lh_whale.py | lh_whale_trades | 2 | +17,09 | forward PAPER (< 30 obchodů) |
| LIQUIDITY V2 | v8-fly-layer-test / liquidity_local.py | liquidity_v2_trades | 19 | −60,60 | forward PAPER (< 30) |
| AROON 1h / SUPERTREND 4h (Swing) | v8-fly-layer-test | swing_paper_trades | 2 / 7 | −100,75 / −212,55 | forward PAPER |
| NEWS_LONG | v8-fly-layer-test | news_paper_trades | 0 | 0 | forward PAPER |
| ELITE V18 / V56 | v8-fly-layer-test | elite_forward_events | 0 / 0 | 0 | forward PAPER; na ladicích datech +4 717,96 / +820,51, brány neprošly |
| COMBINED_BEST_SIGNALS_V1 | v8-fly-layer-test (PR #5) | combined_best_paper_state | 0 | 0 | forward PAPER; replay NEPROŠEL (`research/combined_selection_replay/RESULTS_20261105.md`) |

## B. Výzkumné hypotézy (historie, 110)

Pole: hypotéza | první větev | první výskyt (commit) | soubor s obchody/evidencí | třída → stav. Zdůvodnění, data a metriky po nákladech: `reports/hypothesis-inventory-20261105.md`.

| Hypotéza | Větev | Od | Obchody / evidence | Výsledek |
|---|---|---|---|---|
| elite/V12 | elite-research-v1 | 2026-10-14 (2f72287) | elite/results/20261014_v12/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V15 | elite-research-v1 | 2026-10-14 (3f766ee) | elite/results/20261014_v15/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V18 | elite-research-v1 | 2026-10-14 (763d412) | elite/results/20261014_v18/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V21 | elite-research-v1 | 2026-10-14 (40d2508) | elite/results/20261014_v21/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V24 | elite-research-v1 | 2026-10-14 (e740632) | elite/results/20261014_v24/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V26 | elite-research-v1 | 2026-10-14 (3d5fa3e) | elite/results/20261014_v26/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V28 | elite-research-v1 | 2026-10-14 (22d46ab) | elite/results/20261014_v28/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V30 | elite-research-v1 | 2026-10-14 (3155222) | elite/results/20261014_v30/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V32 | elite-research-v1 | 2026-10-14 (4e7e039) | elite/results/20261014_v32/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V34 | elite-research-v1 | 2026-10-14 (18bbba8) | elite/results/20261014_v34/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V36 | elite-research-v1 | 2026-10-15 (d5c44b0) | elite/results/20261015_v36/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V38 | elite-research-v1 | 2026-10-15 (3b75f06) | elite/results/20261015_v38/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V4 | elite-research-v1 | 2026-10-13 (162b5cf) | — | NEPROŠEL → zamítnuto |
| elite/V40 | elite-research-v1 | 2026-10-15 (849fff4) | elite/results/20261015_v40/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V42 | elite-research-v1 | 2026-10-15 (ecfe715) | elite/results/20261015_v42/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V44 | elite-research-v1 | 2026-10-15 (dba67ed) | elite/results/20261015_v44/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V46 | elite-research-v1 | 2026-10-15 (b11dae0) | elite/results/20261015_v46/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V48 | elite-research-v1 | 2026-10-15 (585448d) | elite/results/20261015_v48/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V49 | elite-research-v1 | 2026-10-15 (31e49a7) | elite/results/20261015_v49/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V51 | elite-research-v1 | 2026-10-16 (7498a3d) | elite/results/20261016_v51/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V52 | elite-research-v1 | 2026-10-16 (5f9f429) | elite/results/20261016_v52/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V53 | elite-research-v1 | 2026-10-16 (808f90c) | elite/results/20261016_v53/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V54 | elite-research-v1 | 2026-10-16 (8b617db) | elite/results/20261016_v54/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V55 | elite-research-v1 | 2026-10-16 (e9d8766) | elite/results/20261016_v55/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V56 | elite-research-v1 | 2026-10-16 (fe8eb84) | elite/results/20261016_v56/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V57 | elite-research-v1 | 2026-10-17 (4336773) | elite/results/20261017_v57/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V59 | elite-research-v1 | 2026-10-17 (fb4e9dc) | elite/results/20261017_v59/evidence.tar.gz | NEPROŠEL → zamítnuto |
| elite/V8 | elite-research-v1 | 2026-10-14 (3b29796) | — | NEPROŠEL → zamítnuto |
| research/ada_state_classifier | ada-state-classifier-research-20261024, triangular-parity-research-20261024 | 2026-10-24 (0337a19) | research/ada_state_classifier_results_20261024.json | NEPROŠEL → zamítnuto |
| research/aggressor_sell_burst | autocorr-regime-research-20261024 | 2026-10-27 (27dd042) | research/aggressor_sell_burst_validation_20261027/trades.json.gz | NEPROŠEL → zamítnuto |
| research/attention_share | autocorr-regime-research-20261024 | 2026-10-26 (a9b4c46) | research/attention_share_validation_20261026/trades.json.gz | NEPROŠEL → zamítnuto |
| research/autocorr | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-24 (97857ed) | research/autocorr_validation_20261024/trades.json.gz | NEPROŠEL → zamítnuto |
| research/autocorr_regime | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-24 (fbc2c1d) | — | NEPROŠEL → zamítnuto |
| research/best | research/best-validation-20261010 | 2026-10-11 (edbcadb) | research/best_validation/results/trades.json.gz | NEPROŠEL → zamítnuto |
| research/best_exits | research/best-validation-20261010 | 2026-10-11 (54b918c) | research/best_exits_20261011/results/trades.json.gz | NEPROŠEL → zamítnuto |
| research/beta_hedged_residual | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+5) | 2026-10-23 (c77ee30) | research/beta_hedged_residual_results_20261023.json | NEPROŠEL → zamítnuto |
| research/bnb_volume_dryup | ada-state-classifier-research-20261024, bnb-volume-dryup-research-20261024, btc-quarterly-carry-research-20261024 (+3) | 2026-10-24 (ae42b18) | research/bnb_volume_dryup_results_20261024.json | NEPROŠEL → zamítnuto |
| research/breadth_capitulation | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-26 (ba2d668) | research/breadth_capitulation_validation_20261026/trades.json.gz | NEPROŠEL → zamítnuto |
| research/broad_dollar_downtrend | autocorr-regime-research-20261024 | 2026-10-28 (47254e8) | research/broad_dollar_downtrend_validation_20261028/trades.json.gz | NEPROŠEL → zamítnuto |
| research/broad_shock_rebound | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+12) | 2026-10-21 (4d02355) | research/broad_shock_rebound_results_20261021.json | NEPROŠEL → zamítnuto |
| research/btc_asset_manager_accumulation_xrp | autocorr-regime-research-20261024 | 2026-11-04 (2ed883d) | research/btc_asset_manager_accumulation_xrp_validation_20261104/trades.json.gz | NEPROŠEL → zamítnuto |
| research/btc_etf_creation_impulse | autocorr-regime-research-20261024 | 2026-10-30 (9cdfe5e) | research/btc_etf_creation_impulse_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/btc_hashrate_shock_recovery | autocorr-regime-research-20261024 | 2026-10-30 (e806f36) | research/btc_hashrate_shock_recovery_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/btc_lead_lag | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-25 (4f8ba1c) | research/btc_lead_lag_validation_20261025/trades.json.gz | NEPROŠEL → zamítnuto |
| research/btc_mempool_clearance_xrp | autocorr-regime-research-20261024 | 2026-11-04 (d6aaf02) | research/btc_mempool_clearance_xrp_validation_20261104/trades.json.gz | NEPROŠEL → zamítnuto |
| research/btc_option_skew_risk_on | autocorr-regime-research-20261024 | 2026-10-30 (c115dfb) | research/btc_option_skew_risk_on_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/btc_quarterly_carry | ada-state-classifier-research-20261024, btc-quarterly-carry-research-20261024, triangular-parity-research-20261024 | 2026-10-24 (546f057) | research/btc_quarterly_carry_results_20261024.json | NEPROŠEL → zamítnuto |
| research/btc_variance_risk_premium | autocorr-regime-research-20261024 | 2026-10-30 (caf3894) | research/btc_variance_risk_premium_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/candle | research/candle-validation-20261019 | 2026-10-19 (abe5dd7) | research/candle_validation_20261019/data_manifest.json | NEPROŠEL → zamítnuto |
| research/combined_selection_replay | claude/xrp-bot-strategy-backtest-7hu2l1, research/combined-selection-replay-20261105, v8-fly-layer-test | 2026-11-05 (2fad28a) | research/combined_selection_replay/reference_vmm_20261022.json | NEPROŠEL → zamítnuto |
| research/core_development_activity | autocorr-regime-research-20261024 | 2026-10-29 (664a9b9) | research/core_development_activity_validation_20261029/trades.json.gz | NEPROŠEL → zamítnuto |
| research/cross_exchange_residual | autocorr-regime-research-20261024 | 2026-10-27 (9276eb8) | research/cross_exchange_residual_validation_20261027/trades.json.gz | NEPROŠEL → zamítnuto |
| research/cross_market_dispersion | research/cross-market-dispersion-20261026 | 2026-10-26 (6ab022f) | research/cross_market_dispersion_20261026/audit.json | NEPROŠEL → zamítnuto |
| research/cross_sectional_rotation | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+14) | 2026-10-20 (f2dac06) | research/cross_sectional_rotation_results_20261020.json | NEPROŠEL → zamítnuto |
| research/defi_yield_rotation | autocorr-regime-research-20261024 | 2026-10-29 (d1e3090) | research/defi_yield_rotation_validation_20261029/trades.json.gz | NEPROŠEL → zamítnuto |
| research/downside_imbalance_short | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+9) | 2026-10-22 (0da15ae) | research/downside_imbalance_short_results_20261022.json | NEPROŠEL → zamítnuto |
| research/eth_funding_extreme | ada-state-classifier-research-20261024, btc-quarterly-carry-research-20261024, eth-funding-extreme-research-20261024 (+2) | 2026-10-24 (6b7e254) | research/eth_funding_extreme_results_20261024.json | NEPROŠEL → zamítnuto |
| research/extreme_fear_contrarian | autocorr-regime-research-20261024 | 2026-10-29 (0230553) | research/extreme_fear_contrarian_validation_20261029/trades.json.gz | NEPROŠEL → zamítnuto |
| research/fib_timeframe | research/fib-timeframe-20261020 | 2026-10-20 (05fca8b) | research/fib_timeframe_20261020/extension_trades.json.gz | NEPROŠEL → zamítnuto |
| research/financial_conditions_easing | autocorr-regime-research-20261024 | 2026-10-29 (1721c42) | research/financial_conditions_easing_validation_20261029/trades.json.gz | NEPROŠEL → zamítnuto |
| research/float_expansion_slowdown | autocorr-regime-research-20261024 | 2026-10-30 (19e0645) | research/float_expansion_slowdown_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/flow_pressure | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+17) | 2026-10-20 (0337a0e) | research/flow_pressure_results_20261020.json | NEPROŠEL → zamítnuto |
| research/funding_reversal | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-25 (39b2eb1) | research/funding_reversal_validation_20261025/trades.json.gz | NEPROŠEL → zamítnuto |
| research/holder_growth_divergence | autocorr-regime-research-20261024 | 2026-10-28 (79d33ec) | research/holder_growth_divergence_validation_20261028/trades.json.gz | NEPROŠEL → zamítnuto |
| research/illiquidity_reversal | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-26 (0217569) | research/illiquidity_reversal_validation_20261026/trades.json.gz | NEPROŠEL → zamítnuto |
| research/large_trade_followthrough | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-25 (466679c) | research/large_trade_followthrough_validation_20261025/trades.json.gz | NEPROŠEL → zamítnuto |
| research/ledger_activity_breadth | autocorr-regime-research-20261024 | 2026-10-27 (9d1676a) | research/audit_ledger_activity_breadth.py | NEPROŠEL → zamítnuto |
| research/ledger_cadence_health | autocorr-regime-research-20261024 | 2026-10-29 (384ccca) | research/audit_ledger_cadence_health.py | NEPROŠEL → zamítnuto |
| research/network_fee_pressure | autocorr-regime-research-20261024 | 2026-10-27 (531d1ba) | research/network_fee_pressure_validation_20261027/trades.json.gz | NEPROŠEL → zamítnuto |
| research/oi_crowding | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-25 (4acf42b) | research/oi_crowding_validation_20261025/trades.json.gz | NEPROŠEL → zamítnuto |
| research/orderbook_depth | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-26 (d5fa1c2) | research/orderbook_depth_validation_20261026/trades.json.gz | NEPROŠEL → zamítnuto |
| research/paper_overlap | research/candle-validation-20261019, research/paper-filters-20261018 | 2026-10-18 (bfd4be5) | research/paper_overlap_20261018/tv_month/tv_trades.json.gz | NEPROŠEL → zamítnuto |
| research/premium_recovery | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-26 (879655d) | research/premium_recovery_validation_20261026/trades.json.gz | NEPROŠEL → zamítnuto |
| research/protocol_activation_event | autocorr-regime-research-20261024 | 2026-10-29 (187157d) | research/protocol_activation_event_validation_20261029/trades.json.gz | NEPROŠEL → zamítnuto |
| research/range_harvest_limit | ada-state-classifier-research-20261024, bnb-volume-dryup-research-20261024, btc-quarterly-carry-research-20261024 (+4) | 2026-10-23 (ccdc5af) | research/range_harvest_limit_results_20261023.json | NEPROŠEL → zamítnuto |
| research/real_yield_easing | autocorr-regime-research-20261024 | 2026-10-29 (a01bce1) | research/real_yield_easing_validation_20261029/trades.json.gz | NEPROŠEL → zamítnuto |
| research/realized_value_discount | autocorr-regime-research-20261024 | 2026-10-28 (05a522e) | research/realized_value_discount_validation_20261028/trades.json.gz | NEPROŠEL → zamítnuto |
| research/recommendations | research/recommendations-20261017 | 2026-10-17 (4f455cf) | research/recommendations_20261017/ledger_cohorts.json | NEPROŠEL → zamítnuto |
| research/relative_strength | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-24 (81fd0d7) | research/relative_strength_validation_20261024/trades.json.gz | NEPROŠEL → zamítnuto |
| research/research | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+17) | 2026-10-20 (1754513) | — | NEPROŠEL → zamítnuto |
| research/residual_snapback | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-25 (88f4039) | research/residual_snapback_validation_20261025/trades.json.gz | NEPROŠEL → zamítnuto |
| research/retest_cost_review | research/candle-validation-20261019 | 2026-10-19 (aef9ceb) | research/retest_cost_review_20261019/data_manifest.json | NEPROŠEL → zamítnuto |
| research/session_transfer | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+7) | 2026-10-23 (1466809) | research/session_transfer_results_20261023.json | NEPROŠEL → zamítnuto |
| research/sol_basis_convergence | ada-state-classifier-research-20261024, btc-quarterly-carry-research-20261024, sol-basis-convergence-research-20261024 (+1) | 2026-10-24 (718f81f) | research/sol_basis_convergence_results_20261024.json | NEPROŠEL → zamítnuto |
| research/sol_eth_pairs | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+13) | 2026-10-21 (38a8f54) | research/sol_eth_pairs_results_20261021.json | NEPROŠEL → zamítnuto |
| research/spot_perp_carry | autocorr-regime-research-20261024 | 2026-10-27 (066f649) | research/spot_perp_carry_validation_20261027/trades.json.gz | NEPROŠEL → zamítnuto |
| research/stable_peg | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-25 (5d69d98) | research/stable_peg_validation_20261025/trades.json.gz | NEPROŠEL → zamítnuto |
| research/stablecoin_liquidity_impulse | autocorr-regime-research-20261024 | 2026-10-28 (5a908b5) | research/stablecoin_liquidity_impulse_validation_20261028/trades.json.gz | NEPROŠEL → zamítnuto |
| research/transfer_utilization_share | autocorr-regime-research-20261024 | 2026-10-30 (9807028) | research/transfer_utilization_share_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/triangular_parity | triangular-parity-research-20261024 | 2026-10-24 (32c7c7a) | research/triangular_parity_results_20261024.json | NEPROŠEL → zamítnuto |
| research/tv | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+29) | 2026-10-12 (3dc3e48) | research/tv_validation_20261012/trades.json.gz | NEPROŠEL → zamítnuto |
| research/vix_shock_recovery | autocorr-regime-research-20261024 | 2026-10-28 (c45b1a4) | research/vix_shock_recovery_validation_20261028/trades.json.gz | NEPROŠEL → zamítnuto |
| research/volatility_compression | autocorr-regime-research-20261024 | 2026-10-27 (8688cb5) | research/volatility_compression_validation_20261027/trades.json.gz | NEPROŠEL → zamítnuto |
| research/volatility_contraction_spot | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+6) | 2026-10-23 (42b3249) | research/volatility_contraction_spot_results_20261023.json | NEPROŠEL → zamítnuto |
| research/volatility_managed_momentum | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+11) | 2026-10-22 (bdb7d8b) | research/volatility_managed_momentum_results_20261022.json | NEPROŠEL → zamítnuto |
| research/weekend | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | 2026-10-24 (97857ed) | research/weekend_validation_20261024/trades.json.gz | NEPROŠEL → zamítnuto |
| research/weekend_carry | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+8) | 2026-10-23 (55dd7c3) | research/weekend_carry_results_20261023.json | NEPROŠEL → zamítnuto |
| research/weekly_inverse_vol_basket | autocorr-regime-research-20261024 | 2026-10-30 (961aa43) | research/weekly_inverse_vol_basket_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| research/whale_vwap | research/whale-vwap-validation-20261013 | 2026-10-13 (175de78) | research/whale_vwap_validation_20261013/trades.json.gz | NEPROŠEL → zamítnuto |
| research/xrp_reverse_repo_liquidity_release | autocorr-regime-research-20261024 | 2026-11-04 (6c5f1c7) | research/xrp_reverse_repo_liquidity_release_validation_20261104/trades.json.gz | NEPROŠEL → zamítnuto |
| research/xrp_session_handoff_reversal | autocorr-regime-research-20261024 | 2026-11-04 (e6c9755) | research/xrp_session_handoff_reversal_validation_20261104/trades.json.gz | NEPROŠEL → zamítnuto |
| research/xrp_yield_curve_steepening | autocorr-regime-research-20261024 | 2026-11-05 (4f8cec6) | research/xrp_yield_curve_steepening_validation_20261105/trades.json.gz | NEPROŠEL → zamítnuto |
| research/xrpl_dex_liquidity_replenishment | autocorr-regime-research-20261024 | 2026-10-30 (110b578) | research/xrpl_dex_liquidity_replenishment_validation_20261030/trades.json.gz | NEPROŠEL → zamítnuto |
| elite/V5 | elite-research-v1 | 2026-10-13 (71729de) | — | NEDOHLEDÁNO → nedohledáno |
| elite/V60 | elite-research-v1 | 2026-10-18 (01c3070) | — | NEDOKONČENO → nedokončeno (test nedoběhl) |
| research/hourly_retest | research/candle-validation-20261019 | 2026-10-19 (9eec861) | — | NEDOKONČENO → nedokončeno (test nedoběhl) |
| research/polymarket_xrp | research/polymarket-xrp-signal-v1-20261028 | 2026-10-28 (09c2476) | research/polymarket_xrp_source_audit_20261029/source_audit.json | NEDOKONČENO → nedokončeno (test nedoběhl) |
| research/polymarket_xrp_signal | autocorr-regime-research-20261024 | 2026-10-29 (6aa6d86) | — | NEDOKONČENO → nedokončeno (test nedoběhl) |
| research/prospective_market_evidence | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+27) | 2026-10-17 (87477ce) | research/prospective_market_evidence_20261017/verification.json | SBĚR DAT → sběr dat (ne strategie) |
| research/xrp_bank_credit_expansion | autocorr-regime-research-20261024 | 2026-11-05 (1824cff) | — | NEDOKONČENO → nedokončeno (test nedoběhl) |

## C. Nové testy autopilota

_(zatím žádné; každý nový test: protokol commitnout před výsledkem, data, parametry, soubor obchodů, výsledek po nákladech, stav)_
