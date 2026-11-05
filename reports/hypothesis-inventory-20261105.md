# Soupis výzkumných hypotéz — 2026-11-05

Vytvořeno pouze čtením 48 vzdálených větví (`git ls-tree` / `git show` / `git log --all`),
žádná z nich nebyla změněna. Generátor: `tools/inventory/build_inventory.py`, poté
10 ručních oprav s uvedeným zdrojem (sloupec „Rozhodnutí“ začíná „ruční:“).
Strojově čitelná verze se seznamy souborů: `reports/hypothesis-inventory-20261105.json`.

**Souhrn:** 110 hypotéz/rodin — 103 NEPROŠEL, 5 NEDOKONČENO, 1 NEDOHLEDÁNO, 1 SBĚR DAT.
Ledger jednotlivých obchodů existuje u 78, soubor se SHA-256 dat u 101.
Chybějící ledger/SHA-256 je uveden jako „chybí“ — nic nebylo dopočteno ani vymyšleno.

Omezení: seskupení podle názvu souboru je heuristické (protokol + kód + validace téže
hypotézy = 1 řádek; ELITE podle čísla verze V*n*). „Rozhodnutí“ je výňatek z validačního
README/reportu/výsledků, nikoli nové hodnocení. „Poprvé“ = datum prvního commitu, který
přidal některý soubor skupiny. Období, parametry a SHA-256 jednotlivých archivů jsou
v souborech uvedených v JSON (`files_with_sha256`). Od 2026-11-05 mohou přibývat další.

| # | Hypotéza | Poprvé | Commit | Větve obsahující první commit | Rozhodnutí (výňatek ze zdroje) | Třída | Ledger obchodů | SHA-256 dat |
|---:|---|---|---|---|---|---|---|---|
| 1 | `elite/V12` | 2026-10-14 | `2f72287` | elite-research-v1 | zamítnuti | **NEPROŠEL** | ano | ano |
| 2 | `elite/V15` | 2026-10-14 | `3f766ee` | elite-research-v1 | neprošel | **NEPROŠEL** | ano | ano |
| 3 | `elite/V18` | 2026-10-14 | `763d412` | elite-research-v1 | neprošla | **NEPROŠEL** | ano | ano |
| 4 | `elite/V21` | 2026-10-14 | `40d2508` | elite-research-v1 | neprošly | **NEPROŠEL** | ano | ano |
| 5 | `elite/V24` | 2026-10-14 | `e740632` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 6 | `elite/V26` | 2026-10-14 | `3d5fa3e` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 7 | `elite/V28` | 2026-10-14 | `22d46ab` | elite-research-v1 | neprošly | **NEPROŠEL** | ano | ano |
| 8 | `elite/V30` | 2026-10-14 | `3155222` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 9 | `elite/V32` | 2026-10-14 | `4e7e039` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 10 | `elite/V34` | 2026-10-14 | `18bbba8` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 11 | `elite/V36` | 2026-10-15 | `d5c44b0` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 12 | `elite/V38` | 2026-10-15 | `3b75f06` | elite-research-v1 | neprošla | **NEPROŠEL** | ano | ano |
| 13 | `elite/V4` | 2026-10-13 | `162b5cf` | elite-research-v1 | ruční: elite/RESEARCH_PROTOCOL_V5.md „V4 is rejected“; v4_audit.json vývoj 228 obchodů, −1 242,88, PF 0,646 | **NEPROŠEL** | chybí | chybí |
| 14 | `elite/V40` | 2026-10-15 | `849fff4` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 15 | `elite/V42` | 2026-10-15 | `ecfe715` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 16 | `elite/V44` | 2026-10-15 | `dba67ed` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 17 | `elite/V46` | 2026-10-15 | `b11dae0` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 18 | `elite/V48` | 2026-10-15 | `585448d` | elite-research-v1 | zamítnuta | **NEPROŠEL** | ano | ano |
| 19 | `elite/V49` | 2026-10-15 | `31e49a7` | elite-research-v1 | zamítnuty | **NEPROŠEL** | ano | ano |
| 20 | `elite/V5` | 2026-10-13 | `71729de` | elite-research-v1 | ruční: jen protokol dávky V5; samostatné rozhodnutí nenalezeno | **NEDOHLEDÁNO** | chybí | chybí |
| 21 | `elite/V51` | 2026-10-16 | `7498a3d` | elite-research-v1 | Rozhodnutí: zamítnuta pro další rezervované ověření i PAPER. Souhrnný zisk není | **NEPROŠEL** | ano | ano |
| 22 | `elite/V52` | 2026-10-16 | `5f9f429` | elite-research-v1 | Rozhodnutí: zamítnuta. Nová strategie odlišná od V18; nepoužívá její průraz | **NEPROŠEL** | ano | ano |
| 23 | `elite/V53` | 2026-10-16 | `808f90c` | elite-research-v1 | Rozhodnutí: zamítnuta pro rezervované ověření i PAPER. Tři kladné bloky a | **NEPROŠEL** | ano | ano |
| 24 | `elite/V54` | 2026-10-16 | `8b617db` | elite-research-v1 | Rozhodnutí: zamítnuta pro rezervované ověření i PAPER. Kladný souhrn nesplňuje | **NEPROŠEL** | ano | ano |
| 25 | `elite/V55` | 2026-10-16 | `e9d8766` | elite-research-v1 | Rozhodnutí: zamítnuta. Výprodej s mimořádným objemem a následné překřížení | **NEPROŠEL** | ano | ano |
| 26 | `elite/V56` | 2026-10-16 | `fe8eb84` | elite-research-v1 | Rozhodnutí: zamítnuta pro rezervované ověření i PAPER. Kladný výnos a malý | **NEPROŠEL** | ano | ano |
| 27 | `elite/V57` | 2026-10-17 | `4336773` | elite-research-v1 | Rozhodnutí: obě zamítnuty. Nové minimum aktivity splnily, finanční brány ne. | **NEPROŠEL** | ano | ano |
| 28 | `elite/V59` | 2026-10-17 | `fb4e9dc` | elite-research-v1 | Rozhodnutí: zamítnuta. Výnos po základních nákladech vzrostl, ale propad | **NEPROŠEL** | ano | ano |
| 29 | `elite/V60` | 2026-10-18 | `01c3070` | elite-research-v1 | ruční: protokol zmrazen 01c3070 (2026-10-18), výsledky necommitnuty | **NEDOKONČENO** | chybí | chybí |
| 30 | `elite/V8` | 2026-10-14 | `3b29796` | elite-research-v1 | Rozhodnutí: žádný kandidát zatím nesplnil předem stanovené podmínky pro další | **NEPROŠEL** | chybí | chybí |
| 31 | `research/ada_state_classifier` | 2026-10-24 | `0337a19` | ada-state-classifier-research-20261024, triangular-parity-research-20261024 | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 32 | `research/aggressor_sell_burst` | 2026-10-27 | `27dd042` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The tick-sequence sell-exhaustion reversal loses in every locked control/OOS year and fails every profitability, stability, drawdown, an | **NEPROŠEL** | ano | ano |
| 33 | `research/attention_share` | 2026-10-26 | `a9b4c46` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The protocol, code and gates were frozen in GitHub commit `a9b4c46350b4e88401646e1bb57608778d22f3f3` before performance evaluation. | **NEPROŠEL** | ano | ano |
| 34 | `research/autocorr` | 2026-10-24 | `97857ed` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 35 | `research/autocorr_regime` | 2026-10-24 | `fbc2c1d` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | rejected | **NEPROŠEL** | chybí | chybí |
| 36 | `research/best` | 2026-10-11 | `edbcadb` | research/best-validation-20261010 | Rozhodnutí: **žádná testovaná varianta nesplnila podmínky pro přechod do kandidátního PAPER provozu. Produkční strategie se nemění.** | **NEPROŠEL** | ano | ano |
| 37 | `research/best_exits` | 2026-10-11 | `54b918c` | research/best-validation-20261010 | NEPROŠLA | **NEPROŠEL** | ano | ano |
| 38 | `research/beta_hedged_residual` | 2026-10-23 | `c77ee30` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+5) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 39 | `research/bnb_volume_dryup` | 2026-10-24 | `ae42b18` | ada-state-classifier-research-20261024, bnb-volume-dryup-research-20261024, btc-quarterly-carry-research-20261024 (+3) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 40 | `research/breadth_capitulation` | 2026-10-26 | `ba2d668` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 41 | `research/broad_dollar_downtrend` | 2026-10-28 | `47254e8` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The external fiat-macro hypothesis, execution rules and | **NEPROŠEL** | ano | ano |
| 42 | `research/broad_shock_rebound` | 2026-10-21 | `4d02355` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+12) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 43 | `research/btc_asset_manager_accumulation_xrp` | 2026-11-04 | `2ed883d` | autocorr-regime-research-20261024 | Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward PAPER promotion or deployment. | **NEPROŠEL** | ano | ano |
| 44 | `research/btc_etf_creation_impulse` | 2026-10-30 | `9cdfe5e` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The protocol and code were saved remotely in commit `9cdfe5e2edfbe68b99f3e2611f67428b09979bc1` before performance evaluation. No thresho | **NEPROŠEL** | ano | ano |
| 45 | `research/btc_hashrate_shock_recovery` | 2026-10-30 | `e806f36` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The completed strategy loses at both cost levels and in four of five OOS years. Do not tune the z-score, lookback or recovery rule and d | **NEPROŠEL** | ano | ano |
| 46 | `research/btc_lead_lag` | 2026-10-25 | `4f8ba1c` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 47 | `research/btc_mempool_clearance_xrp` | 2026-11-04 | `d6aaf02` | autocorr-regime-research-20261024 | Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward PAPER promotion or deployment. | **NEPROŠEL** | ano | ano |
| 48 | `research/btc_option_skew_risk_on` | 2026-10-30 | `c115dfb` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The profitable aggregate does not override failed frozen sample, stability, final-year and concentration gates. Do not tune or invert th | **NEPROŠEL** | ano | ano |
| 49 | `research/btc_quarterly_carry` | 2026-10-24 | `546f057` | ada-state-classifier-research-20261024, btc-quarterly-carry-research-20261024, triangular-parity-research-20261024 | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 50 | `research/btc_variance_risk_premium` | 2026-10-30 | `caf3894` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The fixed hypothesis, threshold, timing, execution and gates were stored in GitHub commit `8014a45b4b8f20ce803c7aacaaf94fc9da6a453f` bef | **NEPROŠEL** | ano | ano |
| 51 | `research/candle` | 2026-10-19 | `abe5dd7` | research/candle-validation-20261019 | ruční: candle_validation_20261019/README „Neither candidate is approved“, breakout/retest nesplnil PF ≥ 1,2 | **NEPROŠEL** | chybí | ano |
| 52 | `research/combined_selection_replay` | 2026-11-05 | `2fad28a` | claude/xrp-bot-strategy-backtest-7hu2l1, research/combined-selection-replay-20261105, v8-fly-layer-test | neprošel | **NEPROŠEL** | chybí | ano |
| 53 | `research/core_development_activity` | 2026-10-29 | `664a9b9` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. | **NEPROŠEL** | ano | ano |
| 54 | `research/cross_exchange_residual` | 2026-10-27 | `9276eb8` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. Rules and gates were frozen on GitHub before historical | **NEPROŠEL** | ano | ano |
| 55 | `research/cross_market_dispersion` | 2026-10-26 | `6ab022f` | research/cross-market-dispersion-20261026 | NEPROŠEL | **NEPROŠEL** | chybí | ano |
| 56 | `research/cross_sectional_rotation` | 2026-10-20 | `f2dac06` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+14) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 57 | `research/defi_yield_rotation` | 2026-10-29 | `d1e3090` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. Positive aggregate history is not sufficient evidence for promotion. | **NEPROŠEL** | ano | ano |
| 58 | `research/downside_imbalance_short` | 2026-10-22 | `0da15ae` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+9) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 59 | `research/eth_funding_extreme` | 2026-10-24 | `6b7e254` | ada-state-classifier-research-20261024, btc-quarterly-carry-research-20261024, eth-funding-extreme-research-20261024 (+2) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 60 | `research/extreme_fear_contrarian` | 2026-10-29 | `0230553` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The frozen sentiment candidate is not promoted to forward PAPER despite positive aggregate history. | **NEPROŠEL** | ano | ano |
| 61 | `research/fib_timeframe` | 2026-10-20 | `05fca8b` | research/fib-timeframe-20261020 | Decision: no production filter/timeframe change. PAPER v13 remains deployed. Paused strategies remain paused. | **NEPROŠEL** | ano | ano |
| 62 | `research/financial_conditions_easing` | 2026-10-29 | `1721c42` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The frozen external financial-conditions hypothesis is rejected and is not promoted to forward PAPER. | **NEPROŠEL** | ano | ano |
| 63 | `research/float_expansion_slowdown` | 2026-10-30 | `19e0645` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The tokenomics hypothesis, 30-day change, past-only 365-day nearest-rank 20th percentile, two-day lag, execution and gates were stored i | **NEPROŠEL** | ano | ano |
| 64 | `research/flow_pressure` | 2026-10-20 | `0337a0e` | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+17) | ruční: research_decision_20261020.md „rejected on XRP 15m“; test PF 0,82 (2×: 0,38) | **NEPROŠEL** | chybí | ano |
| 65 | `research/funding_reversal` | 2026-10-25 | `39b2eb1` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 66 | `research/holder_growth_divergence` | 2026-10-28 | `79d33ec` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The holder-stock/price-divergence hypothesis, rules and | **NEPROŠEL** | ano | ano |
| 67 | `research/hourly_retest` | 2026-10-19 | `9eec861` | research/candle-validation-20261019 | ruční: protokol zmrazen 9eec861 (2026-10-19), výsledky necommitnuty | **NEDOKONČENO** | chybí | chybí |
| 68 | `research/illiquidity_reversal` | 2026-10-26 | `0217569` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | Decision: **NEPROŠEL**. Rules and gates were frozen in GitHub commit `02175691272e35c5614ae8f1204b1ab7226b2403`. The zero-volume/no-imputation ingestion amendme | **NEPROŠEL** | ano | ano |
| 69 | `research/large_trade_followthrough` | 2026-10-25 | `466679c` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 70 | `research/ledger_activity_breadth` | 2026-10-27 | `9d1676a` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The on-chain rules, percentile definition and gates were | **NEPROŠEL** | ano | ano |
| 71 | `research/ledger_cadence_health` | 2026-10-29 | `384ccca` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. A small positive base-cost aggregate is not robust evidence. | **NEPROŠEL** | ano | ano |
| 72 | `research/network_fee_pressure` | 2026-10-27 | `531d1ba` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The fee-pressure rules and gates were committed before | **NEPROŠEL** | ano | ano |
| 73 | `research/oi_crowding` | 2026-10-25 | `4acf42b` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 74 | `research/orderbook_depth` | 2026-10-26 | `d5fa1c2` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | Decision: **NEPROŠEL**. The fixed protocol was stored in commit `d5fa1c2b17a07aa6d4119ba3142ba4a9a15ed8bc`; the missing-archive rule was stored in `8317b33bb5cf | **NEPROŠEL** | ano | ano |
| 75 | `research/paper_overlap` | 2026-10-18 | `bfd4be5` | research/candle-validation-20261019, research/paper-filters-20261018 | reject | **NEPROŠEL** | ano | ano |
| 76 | `research/polymarket_xrp` | 2026-10-28 | `09c2476` | research/polymarket-xrp-signal-v1-20261028 | TEST NEDOKONČEN | **NEDOKONČENO** | chybí | ano |
| 77 | `research/polymarket_xrp_signal` | 2026-10-29 | `6aa6d86` | autocorr-regime-research-20261024 | ruční: protokol 6aa6d86; audit zdroje „TEST NEDOKONČEN“ | **NEDOKONČENO** | chybí | chybí |
| 78 | `research/premium_recovery` | 2026-10-26 | `879655d` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 79 | `research/prospective_market_evidence` | 2026-10-17 | `87477ce` | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+27) | ruční: archiv tržních snímků, ne obchodní strategie | **SBĚR DAT** | chybí | ano |
| 80 | `research/protocol_activation_event` | 2026-10-29 | `187157d` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The fixed protocol, source feasibility, code and gates were stored in GitHub commit `164ddea10785c33b81da1404f5dc7d4878a0d865` before an | **NEPROŠEL** | ano | ano |
| 81 | `research/range_harvest_limit` | 2026-10-23 | `ccdc5af` | ada-state-classifier-research-20261024, bnb-volume-dryup-research-20261024, btc-quarterly-carry-research-20261024 (+4) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 82 | `research/real_yield_easing` | 2026-10-29 | `a01bce1` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The frozen external real-rate hypothesis does not qualify for forward PAPER promotion. | **NEPROŠEL** | ano | ano |
| 83 | `research/realized_value_discount` | 2026-10-28 | `05a522e` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The cost-basis valuation hypothesis, rules and gates | **NEPROŠEL** | ano | ano |
| 84 | `research/recommendations` | 2026-10-17 | `4f455cf` | research/recommendations-20261017 | neprošla | **NEPROŠEL** | ano | ano |
| 85 | `research/relative_strength` | 2026-10-24 | `81fd0d7` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | Decision: **NEPROŠEL**. Historical net profit is not sufficient evidence for promotion. | **NEPROŠEL** | ano | ano |
| 86 | `research/research` | 2026-10-20 | `1754513` | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+17) | rejected | **NEPROŠEL** | chybí | chybí |
| 87 | `research/residual_snapback` | 2026-10-25 | `88f4039` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 88 | `research/retest_cost_review` | 2026-10-19 | `aef9ceb` | research/candle-validation-20261019 | Decision: REJECT FOR DEPLOYMENT. This is offline research, not a change to any running bot. | **NEPROŠEL** | chybí | ano |
| 89 | `research/session_transfer` | 2026-10-23 | `1466809` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+7) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 90 | `research/sol_basis_convergence` | 2026-10-24 | `718f81f` | ada-state-classifier-research-20261024, btc-quarterly-carry-research-20261024, sol-basis-convergence-research-20261024 (+1) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 91 | `research/sol_eth_pairs` | 2026-10-21 | `38a8f54` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+13) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 92 | `research/spot_perp_carry` | 2026-10-27 | `066f649` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The market-neutral funding-carry hypothesis failed the frozen historical gates and is not eligible for forward PAPER promotion. | **NEPROŠEL** | ano | ano |
| 93 | `research/stable_peg` | 2026-10-25 | `5d69d98` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 94 | `research/stablecoin_liquidity_impulse` | 2026-10-28 | `5a908b5` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The external-liquidity hypothesis, execution rules and | **NEPROŠEL** | ano | ano |
| 95 | `research/transfer_utilization_share` | 2026-10-30 | `9807028` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The compositional hypothesis, 180-day lookback, nearest-rank 80th percentile, two-day lag, execution and gates were stored in GitHub com | **NEPROŠEL** | ano | ano |
| 96 | `research/triangular_parity` | 2026-10-24 | `32c7c7a` | triangular-parity-research-20261024 | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 97 | `research/tv` | 2026-10-12 | `3dc3e48` | ada-state-classifier-research-20261024, autocorr-regime-research-20261024, beta-hedged-residual-research-20261023 (+29) | ruční: tv_validation_20261012/README — všech 9 variant záporných, TV pozastaven | **NEPROŠEL** | ano | ano |
| 98 | `research/vix_shock_recovery` | 2026-10-28 | `c45b1a4` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The external equity-volatility recovery hypothesis, | **NEPROŠEL** | ano | ano |
| 99 | `research/volatility_compression` | 2026-10-27 | `8688cb5` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. The low-volatility-to-breakout hypothesis fails the frozen sample, aggregate profitability, stress, annual-stability, and concentration  | **NEPROŠEL** | ano | ano |
| 100 | `research/volatility_contraction_spot` | 2026-10-23 | `42b3249` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+6) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 101 | `research/volatility_managed_momentum` | 2026-10-22 | `bdb7d8b` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+11) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 102 | `research/weekend` | 2026-10-24 | `97857ed` | autocorr-regime-research-20261024, research/cross-market-dispersion-20261026 | NEPROSEL | **NEPROŠEL** | ano | ano |
| 103 | `research/weekend_carry` | 2026-10-23 | `55dd7c3` | ada-state-classifier-research-20261024, beta-hedged-residual-research-20261023, bnb-volume-dryup-research-20261024 (+8) | passes_historical_gate": false | **NEPROŠEL** | chybí | ano |
| 104 | `research/weekly_inverse_vol_basket` | 2026-10-30 | `961aa43` | autocorr-regime-research-20261024 | Decision: **NEPROŠEL**. Do not tune the universe, volatility window, cap, stop or rebalance schedule on these observations, and do not start forward PAPER. | **NEPROŠEL** | ano | ano |
| 105 | `research/whale_vwap` | 2026-10-13 | `175de78` | research/whale-vwap-validation-20261013 | Decision: **no tested replacement is eligible for promotion; VWAP_REVERSION remains paused.** | **NEPROŠEL** | ano | ano |
| 106 | `research/xrp_bank_credit_expansion` | 2026-11-05 | `1824cff` | autocorr-regime-research-20261024 | ruční: předregistrováno 1824cff (2026-11-05), výsledky zatím nejsou | **NEDOKONČENO** | chybí | chybí |
| 107 | `research/xrp_reverse_repo_liquidity_release` | 2026-11-04 | `6c5f1c7` | autocorr-regime-research-20261024 | Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward | **NEPROŠEL** | ano | ano |
| 108 | `research/xrp_session_handoff_reversal` | 2026-11-04 | `e6c9755` | autocorr-regime-research-20261024 | Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no forward PAPER promotion or deployment. | **NEPROŠEL** | ano | ano |
| 109 | `research/xrp_yield_curve_steepening` | 2026-11-05 | `4f8cec6` | autocorr-regime-research-20261024 | Final decision on 2026-11-05: **NEPROSEL**. Offline research only; no forward | **NEPROŠEL** | ano | ano |
| 110 | `research/xrpl_dex_liquidity_replenishment` | 2026-10-30 | `110b578` | autocorr-regime-research-20261024 | Final decision on 2026-11-04: **NEPROSEL**. Offline research only; no deployment or forward PAPER promotion. | **NEPROŠEL** | ano | ano |
