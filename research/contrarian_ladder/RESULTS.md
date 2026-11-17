# Kontrariánský žebřík 20/30/40 %, 8 aktiv — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná varianta, 8 rukávů po 50 % základ + 50 % žebřík.

| kritérium | splněno |
|---|---|
| A1_validation_sharpe_and_dd_beat_bh_x1 | ano |
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

DSR validace ×1 (N = 162): 0.275; walk-forward kladných let: 3/4.

## Strategie vs. buy & hold rovnovážného koše 8 aktiv

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | tranše | P/L žebříku | PF tranší | bez top 3 | poplatky | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 20850.34 | 208.5 | 0.97 | 86.6 | 81 | 3.77 | 1.00 | 17089.10 | 141.64 | 416.9 | 1.16 | 87.7 |
| tuning | ×2 | 20745.16 | 207.5 | 0.97 | 86.6 | 81 | -42.03 | 1.00 | 17025.66 | 281.79 | 415.7 | 1.16 | 87.7 |
| tuning | ×3 | 20640.61 | 206.4 | 0.97 | 86.6 | 81 | -87.34 | 0.99 | 16962.35 | 420.45 | 414.6 | 1.16 | 87.7 |
| validation | ×1 | 22720.51 | 227.2 | 1.49 | 34.9 | 58 | 8735.66 | 27.01 | 21517.92 | 84.72 | 279.7 | 1.49 | 40.4 |
| validation | ×2 | 22595.59 | 226.0 | 1.48 | 35.0 | 58 | 8654.36 | 26.26 | 21403.24 | 168.93 | 278.8 | 1.48 | 40.4 |
| validation | ×3 | 22471.31 | 224.7 | 1.48 | 35.0 | 58 | 8573.59 | 25.47 | 21289.13 | 252.64 | 278.0 | 1.48 | 40.4 |
| final_test | ×1 | -3678.86 | -36.8 | -0.19 | 61.7 | 33 | -1608.86 | 0.34 | -4104.69 | 24.98 | -41.4 | -0.18 | 64.9 |
| final_test | ×2 | -3697.42 | -37.0 | -0.19 | 61.7 | 33 | -1620.69 | 0.34 | -4120.83 | 49.89 | -41.5 | -0.19 | 64.9 |
| final_test | ×3 | -3715.92 | -37.2 | -0.19 | 61.7 | 33 | -1632.47 | 0.34 | -4136.92 | 74.71 | -41.7 | -0.19 | 64.9 |

## Robustnost

| test | čistý P/L | výnos % | Sharpe | DD % | tranše |
|---|---|---|---|---|---|
| soused L15_25_35, validace ×2 | 22688.16 | 226.9 | 1.47 | 34.9 | 68 |
| soused L25_35_45, validace ×2 | 22956.87 | 229.6 | 1.53 | 32.9 | 50 |
| WF 2021 ×2 (B&H 778.9 %) | 43342.17 | 433.4 | 1.93 | 68.8 | 59 |
| WF 2022 ×2 (B&H -63.4 %) | -6285.92 | -62.9 | -0.93 | 66.5 | 24 |
| WF 2023 ×2 (B&H 86.1 %) | 8260.04 | 82.6 | 1.55 | 27.5 | 31 |
| WF 2024 ×2 (B&H 111.8 %) | 8408.88 | 84.1 | 1.49 | 34.3 | 33 |

## Informačně (×1, NEJSOU kritériem)

| varianta | výnos % | Sharpe | DD % | tranše |
|---|---|---|---|---|
| static_50_50/validation | 139.8 | 1.38 | 30.0 | 0 |
| static_50_50/final_test | -20.7 | -0.33 | 36.2 | 0 |
| BTC_sleeve_only | 293.8 | 2.00 | 19.4 | 5 |
| BH_BTC | 464.4 | 2.02 | 26.2 | 0 |

Pozn.: `trades.csv` řádky BASE (základ rukávu) + TRANCHE (tranše); součet net_pnl bloku = čistý P/L bloku.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
