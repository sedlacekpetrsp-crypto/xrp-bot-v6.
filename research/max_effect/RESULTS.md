# MAX efekt, 8 USDT-M perpů, tržně neutrální — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — zvolená varianta L14_H28 (výběr na ladění ×1 podle čistého zisku).

| kritérium | splněno |
|---|---|
| A1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| A2_validation_trades_ge_30 | ano |
| A3_validation_x2_pf_gt_1_2_and_net_gt_0 | NE |
| A4_validation_x1_net_without_top3_gt_0 | NE |
| A5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | ano |
| B1_val_x2_profit_pf | NE |
| B2_dd_le_0_6_bh | NE |
| B3_final_x2_profit | ano |
| B4_val_wo_top3 | NE |
| B5_trades_ge_20 | ano |
| B6_tuning_x1_profit | ano |
| dsr_ge_0_95 | NE |
| neighbors_val_x2_profit | NE |
| walk_forward_ge_3_of_4 | ano |

DSR validace ×1 (N = 170, podmíněné — R10): 0.023; walk-forward kladných let: 4/4.

## Mřížka na ladění ×1

| varianta | čistý P/L | Sharpe | DD % | nohy |
|---|---|---|---|---|
| L14_H14 | 3147.07 | 0.51 | 37.9 | 330 |
| L14_H28 | 12210.42 | 1.09 | 26.6 | 168 |
| L28_H14 | -3407.49 | -0.73 | 45.9 | 318 |
| L28_H28 | 7388.06 | 0.91 | 31.5 | 162 |

## Strategie vs. buy & hold rovnovážného koše 8 perpů

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | nohy | PF | bez top 3 | funding | náklady | likvid. | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 12210.42 | 122.1 | 1.09 | 26.6 | 168 | 1.33 | -2886.79 | -1356.83 | 760.44 | 8 | 517.1 | 1.25 | 86.0 |
| tuning | ×2 | 11380.68 | 113.8 | 1.05 | 27.2 | 168 | 1.31 | -3577.83 | -1340.20 | 1491.12 | 8 | 516.1 | 1.25 | 86.0 |
| tuning | ×3 | 10580.89 | 105.8 | 1.01 | 27.9 | 168 | 1.29 | -4240.21 | -1323.99 | 2193.10 | 8 | 515.2 | 1.25 | 86.0 |
| validation | ×1 | 1702.32 | 17.0 | 0.52 | 38.8 | 156 | 1.11 | -4295.33 | 74.57 | 401.08 | 4 | 472.1 | 1.73 | 37.3 |
| validation | ×2 | 1281.62 | 12.8 | 0.42 | 40.2 | 156 | 1.09 | -4579.05 | 75.44 | 788.80 | 4 | 471.2 | 1.73 | 37.3 |
| validation | ×3 | 875.48 | 8.8 | 0.32 | 41.5 | 156 | 1.06 | -4852.42 | 76.29 | 1163.60 | 4 | 470.4 | 1.73 | 37.3 |
| final_test | ×1 | 949.53 | 9.5 | 0.51 | 10.1 | 138 | 1.09 | -643.46 | -21.81 | 339.94 | 0 | -42.4 | -0.21 | 64.9 |
| final_test | ×2 | 607.53 | 6.1 | 0.35 | 10.6 | 138 | 1.06 | -966.18 | -20.89 | 669.44 | 0 | -42.6 | -0.21 | 65.0 |
| final_test | ×3 | 275.75 | 2.8 | 0.19 | 11.3 | 138 | 1.03 | -1278.87 | -20.00 | 988.82 | 0 | -42.8 | -0.21 | 65.0 |

## Robustnost

| test | čistý P/L | výnos % | Sharpe | DD % | nohy |
|---|---|---|---|---|---|
| soused L14_H14, validace ×2 | -3684.74 | -36.8 | -1.29 | 51.1 | 312 |
| soused L28_H28, validace ×2 | 1394.52 | 13.9 | 0.46 | 34.0 | 156 |
| WF 2021 ×2 (B&H 2166.2 %) | 617.63 | 6.2 | 0.38 | 35.7 | 72 |
| WF 2022 ×2 (B&H -66.4 %) | 171.26 | 1.7 | 0.20 | 8.9 | 66 |
| WF 2023 ×2 (B&H 180.2 %) | 170.63 | 1.7 | 0.19 | 24.4 | 72 |
| WF 2024 ×2 (B&H 118.4 %) | 2463.29 | 24.6 | 1.23 | 19.5 | 78 |

## Informačně (NEJSOU kritériem)

- exposure/tuning: beta ke koši 0.09, korelace ke koši 0.23, k BTC 0.06
- exposure/validation: beta ke koši -0.02, korelace ke koši -0.06, k BTC -0.09
- placebo_reverse/validation/x1: P/L 794.60, výnos 7.9 %, Sharpe 0.32, DD 28.1 %
- exposure/final_test: beta ke koši -0.08, korelace ke koši -0.46, k BTC -0.32
- placebo_reverse/final_test/x1: P/L -1582.85, výnos -15.8 %, Sharpe -0.82, DD 22.3 %

Pozn.: `trades.csv` = každá noha; součet net_pnl bloku (variant, mode, period, cost_multiplier) = čistý P/L bloku.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
