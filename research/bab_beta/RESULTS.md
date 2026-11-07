# Betting-against-beta, 8 USDT-M perpů — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — zvolená varianta W60_H14 (výběr na ladění ×1 podle čistého zisku).

| kritérium | splněno |
|---|---|
| A1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| A2_validation_trades_ge_30 | ano |
| A3_validation_x2_pf_gt_1_2_and_net_gt_0 | NE |
| A4_validation_x1_net_without_top3_gt_0 | NE |
| A5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |
| B1_val_x2_profit_pf | NE |
| B2_dd_le_0_6_bh | ano |
| B3_final_x2_profit | NE |
| B4_val_wo_top3 | NE |
| B5_trades_ge_20 | ano |
| B6_tuning_x1_profit | ano |
| dsr_ge_0_95 | NE |
| neighbors_val_x2_profit | NE |
| walk_forward_ge_3_of_4 | NE |

DSR validace ×1 (N = 166, podmíněné — R10): 0.011; walk-forward kladných let: 2/4.

## Mřížka na ladění ×1

| varianta | čistý P/L | Sharpe | DD % | nohy |
|---|---|---|---|---|
| W60_H7 | 5186.27 | 0.82 | 32.3 | 612 |
| W60_H14 | 10242.24 | 1.11 | 28.7 | 306 |
| W120_H7 | 6736.42 | 1.01 | 26.1 | 558 |
| W120_H14 | 8361.72 | 1.03 | 24.3 | 282 |

## Strategie vs. buy & hold rovnovážného koše 8 perpů

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | nohy | PF | bez top 3 | funding | náklady | likvid. | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 10242.24 | 102.4 | 1.11 | 28.7 | 306 | 1.26 | -999.29 | -2295.72 | 1300.95 | 7 | 517.1 | 1.25 | 86.0 |
| tuning | ×2 | 8865.41 | 88.7 | 1.02 | 29.4 | 306 | 1.23 | -2184.10 | -2259.22 | 2508.40 | 7 | 516.1 | 1.25 | 86.0 |
| tuning | ×3 | 7580.67 | 75.8 | 0.92 | 30.1 | 306 | 1.20 | -3280.66 | -2223.72 | 3628.60 | 7 | 515.2 | 1.25 | 86.0 |
| validation | ×1 | 749.04 | 7.5 | 0.32 | 16.0 | 312 | 1.04 | -1892.19 | 15.90 | 771.61 | 4 | 472.1 | 1.73 | 37.3 |
| validation | ×2 | -4.78 | -0.0 | 0.07 | 20.0 | 312 | 1.00 | -2530.16 | 17.29 | 1489.27 | 4 | 471.2 | 1.73 | 37.3 |
| validation | ×3 | -706.59 | -7.1 | -0.17 | 24.5 | 312 | 0.96 | -3122.86 | 18.54 | 2156.67 | 4 | 470.4 | 1.73 | 37.3 |
| final_test | ×1 | 343.84 | 3.4 | 0.25 | 11.6 | 282 | 1.03 | -1154.28 | -104.16 | 642.83 | 0 | -42.4 | -0.21 | 64.9 |
| final_test | ×2 | -303.76 | -3.0 | -0.14 | 12.3 | 282 | 0.98 | -1744.30 | -99.98 | 1245.06 | 0 | -42.6 | -0.21 | 65.0 |
| final_test | ×3 | -911.56 | -9.1 | -0.53 | 13.0 | 282 | 0.93 | -2297.11 | -95.98 | 1809.19 | 0 | -42.8 | -0.21 | 65.0 |

## Robustnost

| test | čistý P/L | výnos % | Sharpe | DD % | nohy |
|---|---|---|---|---|---|
| soused W60_H7, validace ×2 | -2204.23 | -22.0 | -0.82 | 30.7 | 624 |
| soused W120_H14, validace ×2 | 786.05 | 7.9 | 0.34 | 15.7 | 312 |
| WF 2021 ×2 (B&H 2166.2 %) | 1566.06 | 15.7 | 0.56 | 34.5 | 150 |
| WF 2022 ×2 (B&H -66.4 %) | -329.93 | -3.3 | -0.28 | 14.5 | 108 |
| WF 2023 ×2 (B&H 180.2 %) | -564.23 | -5.6 | -0.39 | 14.9 | 150 |
| WF 2024 ×2 (B&H 118.4 %) | 399.61 | 4.0 | 0.32 | 16.5 | 156 |

## Informačně (NEJSOU kritériem)

- exposure/tuning: beta ke koši 0.11, korelace ke koši 0.34, k BTC 0.42
- exposure/validation: beta ke koši 0.06, korelace ke koši 0.23, k BTC 0.20
- placebo_reverse/validation/x1: P/L -1562.67, výnos -15.6 %, Sharpe -0.52, DD 22.4 %
- exposure/final_test: beta ke koši 0.04, korelace ke koši 0.27, k BTC 0.37
- placebo_reverse/final_test/x1: P/L -1626.23, výnos -16.3 %, Sharpe -1.02, DD 24.2 %

Pozn.: `trades.csv` = každá noha; součet net_pnl bloku (variant, mode, period, cost_multiplier) = čistý P/L bloku.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
