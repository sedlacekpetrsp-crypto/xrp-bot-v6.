# Volatilitní cílení BTC 40 % — výsledky (protokol `PROTOCOL.md` + dodatek 1)

**Verdikt: ZAMÍTNUTO** — jediná varianta cíl 40 %, pásmo ±10 p. b., σ30, long-only bez páky.

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

DSR validace ×1 (N = 148): 0.643; walk-forward kladných let: 3/4.

## Strategie vs. buy & hold BTC

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | úseky | PF | bez top 3 | poplatky | prům. váha | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 1970.22 | 19.7 | 0.40 | 64.2 | 43 | 1.06 | -13815.85 | 152.68 | 0.63 | 41.7 | 0.57 | 76.6 |
| tuning | ×2 | 1862.63 | 18.6 | 0.39 | 64.3 | 43 | 1.06 | -13876.02 | 303.93 | 0.63 | 41.3 | 0.56 | 76.6 |
| tuning | ×3 | 1756.08 | 17.6 | 0.38 | 64.4 | 43 | 1.05 | -13935.34 | 453.77 | 0.63 | 41.0 | 0.56 | 76.6 |
| validation | ×1 | 39222.09 | 392.2 | 2.14 | 20.7 | 35 | 3.47 | 19898.60 | 210.41 | 0.86 | 464.4 | 2.02 | 26.2 |
| validation | ×2 | 38848.44 | 388.5 | 2.13 | 20.7 | 35 | 3.44 | 19645.97 | 418.66 | 0.86 | 463.1 | 2.01 | 26.2 |
| validation | ×3 | 38560.99 | 385.6 | 2.12 | 20.7 | 35 | 3.36 | 19436.39 | 627.63 | 0.86 | 461.8 | 2.01 | 26.2 |
| final_test | ×1 | -1697.05 | -17.0 | -0.09 | 50.6 | 15 | 0.71 | -5165.33 | 40.87 | 0.89 | -17.3 | -0.03 | 53.0 |
| final_test | ×2 | -1735.55 | -17.4 | -0.09 | 50.7 | 15 | 0.70 | -5191.71 | 81.54 | 0.89 | -17.5 | -0.03 | 53.0 |
| final_test | ×3 | -1773.85 | -17.7 | -0.10 | 50.7 | 15 | 0.70 | -5217.94 | 122.01 | 0.89 | -17.7 | -0.03 | 53.0 |

## Robustnost

| test | čistý P/L | výnos % | Sharpe | DD % | úseky |
|---|---|---|---|---|---|
| soused T30, validace ×2 | 25785.07 | 257.9 | 2.08 | 19.8 | 43 |
| soused T50, validace ×2 | 45306.90 | 453.1 | 2.09 | 24.0 | 17 |
| WF 2021 ×2 (B&H 59.1 %) | 3190.41 | 31.9 | 0.87 | 31.0 | 14 |
| WF 2022 ×2 (B&H -64.4 %) | -5421.69 | -54.2 | -1.62 | 55.4 | 25 |
| WF 2023 ×2 (B&H 154.4 %) | 12477.11 | 124.8 | 2.25 | 20.0 | 17 |
| WF 2024 ×2 (B&H 120.3 %) | 11540.81 | 115.4 | 2.00 | 20.7 | 19 |

## Informačně (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | výnos % | Sharpe | DD % | úseky | B&H výnos % | B&H Sharpe | B&H DD % |
|---|---|---|---|---|---|---|---|
| BTC_T30 | 261.0 | 2.09 | 19.7 | 43 | 464.4 | 2.02 | 26.2 |
| BTC_T60 | 447.9 | 2.06 | 25.1 | 7 | 464.4 | 2.02 | 26.2 |
| ETH_T40 | 174.1 | 1.38 | 31.8 | 43 | 178.4 | 1.18 | 45.3 |

Pozn.: `trades.csv` = úseky mezi úpravami; součet net_pnl bloku (variant, period, cost_multiplier) = čistý P/L bloku.
Úsek nese náklady úpravy, která ho ukončuje (první i počáteční nákup, poslední i likvidaci).

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
