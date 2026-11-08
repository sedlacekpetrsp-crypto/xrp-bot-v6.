# Průřezové momentum long-short, 8 USDT-M perpů, tržně neutrální — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — zvolená varianta LB56_S7 (výběr na ladění ×1 podle čistého zisku).

| kritérium | splněno |
|---|---|
| A1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| A2_validation_trades_ge_30 | ano |
| A3_validation_x2_pf_gt_1_2_and_net_gt_0 | NE |
| A4_validation_x1_net_without_top3_gt_0 | NE |
| A5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |
| B1_val_x2_profit_pf | NE |
| B2_dd_le_0_6_bh | NE |
| B3_final_x2_profit | NE |
| B4_val_wo_top3 | NE |
| B5_trades_ge_20 | ano |
| B6_tuning_x1_profit | ano |
| dsr_ge_0_95 | NE |
| neighbors_val_x2_profit | NE |
| walk_forward_ge_3_of_4 | NE |

DSR validace ×1 (N = 198, V[SR] = 0.5): 0.002; walk-forward kladných let: 1/4.

## Mřížka na ladění ×1

| varianta | čistý P/L | Sharpe | DD % | nohy |
|---|---|---|---|---|
| LB28_S0 | 6892.02 | 0.79 | 29.0 | 108 |
| LB28_S7 | 1821.84 | 0.38 | 40.2 | 108 |
| LB56_S0 | 4038.44 | 0.52 | 35.6 | 104 |
| LB56_S7 | 8681.43 | 0.74 | 36.3 | 104 |

## Strategie vs. buy & hold rovnovážného koše 8 perpů

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | nohy | PF | bez top 3 | funding | náklady | likvid. | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 8681.43 | 86.8 | 0.74 | 36.3 | 104 | 1.28 | -8227.20 | -947.28 | 606.05 | 5 | 517.1 | 1.25 | 86.0 |
| tuning | ×2 | 8020.88 | 80.2 | 0.71 | 37.7 | 104 | 1.26 | -8726.47 | -944.59 | 1189.65 | 5 | 516.1 | 1.25 | 86.0 |
| tuning | ×3 | 7382.83 | 73.8 | 0.68 | 39.0 | 104 | 1.24 | -9204.56 | -941.84 | 1751.55 | 5 | 515.2 | 1.25 | 86.0 |
| validation | ×1 | -620.45 | -6.2 | -0.05 | 27.8 | 104 | 0.96 | -4944.80 | -67.41 | 318.12 | 5 | 472.1 | 1.73 | 37.3 |
| validation | ×2 | -952.64 | -9.5 | -0.14 | 28.9 | 104 | 0.93 | -5148.85 | -67.15 | 624.91 | 5 | 471.2 | 1.73 | 37.3 |
| validation | ×3 | -1273.49 | -12.7 | -0.22 | 29.9 | 104 | 0.91 | -5345.41 | -66.91 | 920.75 | 5 | 470.4 | 1.73 | 37.3 |
| final_test | ×1 | -1553.03 | -15.5 | -0.68 | 24.3 | 92 | 0.86 | -3542.05 | 1.59 | 297.12 | 0 | -42.4 | -0.21 | 64.9 |
| final_test | ×2 | -1818.97 | -18.2 | -0.81 | 26.3 | 92 | 0.83 | -3780.69 | 1.55 | 585.55 | 0 | -42.6 | -0.21 | 65.0 |
| final_test | ×3 | -2076.89 | -20.8 | -0.95 | 28.2 | 92 | 0.81 | -4011.63 | 1.51 | 865.53 | 0 | -42.8 | -0.21 | 65.0 |

## Robustnost

| test | čistý P/L | výnos % | Sharpe | DD % | nohy |
|---|---|---|---|---|---|
| soused LB28_S7, validace ×2 | -615.02 | -6.2 | -0.05 | 21.5 | 104 |
| soused LB56_S0, validace ×2 | -805.78 | -8.1 | -0.10 | 24.0 | 104 |
| WF 2021 ×2 (B&H 2166.2 %) | 2013.56 | 20.1 | 0.58 | 32.9 | 48 |
| WF 2022 ×2 (B&H -66.4 %) | -1807.76 | -18.1 | -1.76 | 20.9 | 32 |
| WF 2023 ×2 (B&H 180.2 %) | -1377.67 | -13.8 | -0.78 | 28.9 | 48 |
| WF 2024 ×2 (B&H 118.4 %) | -465.44 | -4.7 | -0.11 | 14.9 | 52 |

## Informačně (NEJSOU kritériem)

- exposure/tuning: beta ke koši 0.16, korelace ke koši 0.27, k BTC 0.03
- exposure/validation: beta ke koši 0.06, korelace ke koši 0.17, k BTC 0.23
- placebo_reverse/validation/x1: P/L 5153.50, výnos 51.5 %, Sharpe 0.94, DD 41.4 %
- exposure/final_test: beta ke koši -0.04, korelace ke koši -0.19, k BTC -0.17
- placebo_reverse/final_test/x1: P/L 767.65, výnos 7.7 %, Sharpe 0.39, DD 11.3 %
- dsr_validation_x1_var_0_40: DSR 0.005

Pozn.: `trades.csv` = každá noha; součet net_pnl bloku (variant, mode, period, cost_multiplier) = čistý P/L bloku.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
