# Blízkost 52týdennímu maximu, 8 aktiv — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná varianta top 3, měsíčně, stejné váhy, 100 % investováno.

| kritérium | splněno |
|---|---|
| A1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| A2_validation_trades_ge_30 | ano |
| A3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| A4_validation_x1_net_without_top3_gt_0 | ano |
| A5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |
| B1_val_x2_profit_pf | ano |
| B2_dd_le_0_6_bh | NE |
| B3_final_x2_profit | NE |
| B4_val_wo_top3 | ano |
| B5_trades_ge_20 | ano |
| B6_tuning_x1_profit | ano |
| dsr_ge_0_95 | NE |
| neighbors_val_x2_profit | ano |
| walk_forward_ge_3_of_4 | ano |

DSR validace ×1 (N = 151): 0.263; walk-forward kladných let: 3/4.

## Strategie vs. buy & hold rovnovážného koše 8 aktiv

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | bez top 3 | poplatky | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 75801.26 | 758.0 | 1.19 | 78.8 | 84 | 1.14 | -152961.24 | 2190.26 | 416.9 | 1.16 | 87.7 |
| tuning | ×2 | 74364.29 | 743.6 | 1.18 | 78.8 | 84 | 1.14 | -152374.22 | 4332.02 | 415.7 | 1.16 | 87.7 |
| tuning | ×3 | 72953.16 | 729.5 | 1.18 | 78.9 | 84 | 1.14 | -151783.17 | 6426.25 | 414.6 | 1.16 | 87.7 |
| validation | ×1 | 27630.23 | 276.3 | 1.44 | 32.1 | 72 | 2.11 | 3864.85 | 382.97 | 279.7 | 1.49 | 40.4 |
| validation | ×2 | 26936.65 | 269.4 | 1.43 | 32.4 | 72 | 2.09 | 3549.84 | 756.76 | 278.8 | 1.48 | 40.4 |
| validation | ×3 | 26256.66 | 262.6 | 1.41 | 32.7 | 72 | 2.07 | 3241.87 | 1121.58 | 278.0 | 1.48 | 40.4 |
| final_test | ×1 | -2618.12 | -26.2 | -0.10 | 59.8 | 66 | 0.78 | -4959.17 | 80.39 | -41.4 | -0.18 | 64.9 |
| final_test | ×2 | -2686.52 | -26.9 | -0.11 | 59.9 | 66 | 0.77 | -5014.33 | 159.97 | -41.5 | -0.19 | 64.9 |
| final_test | ×3 | -2754.19 | -27.5 | -0.12 | 59.9 | 66 | 0.77 | -5068.85 | 238.74 | -41.7 | -0.19 | 64.9 |

## Robustnost

| test | čistý P/L | výnos % | Sharpe | DD % | obchody |
|---|---|---|---|---|---|
| soused TOP2, validace ×2 | 17533.61 | 175.3 | 1.17 | 41.8 | 48 |
| soused TOP4, validace ×2 | 38933.04 | 389.3 | 1.66 | 39.5 | 96 |
| WF 2021 ×2 (B&H 778.9 %) | 146264.43 | 1462.6 | 2.11 | 57.0 | 36 |
| WF 2022 ×2 (B&H -63.4 %) | -7161.13 | -71.6 | -1.39 | 72.5 | 36 |
| WF 2023 ×2 (B&H 86.1 %) | 7254.19 | 72.5 | 1.36 | 32.4 | 36 |
| WF 2024 ×2 (B&H 111.8 %) | 11340.42 | 113.4 | 1.49 | 32.3 | 36 |

## Informačně (validace ×1, NEJSOU kritériem)

| varianta | výnos % | Sharpe | DD % | obchody |
|---|---|---|---|---|
| placebo_BOTTOM3 | 270.3 | 1.35 | 41.8 | 72 |
| EQW8_monthly_rebalance | 342.5 | 1.61 | 39.1 | 192 |
| BH_BTC | 464.4 | 2.02 | 26.2 | 0 |

Pozn.: `trades.csv` = slot aktiva v měsíci; součet net_pnl bloku (variant, period, cost_multiplier) = čistý P/L bloku.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
