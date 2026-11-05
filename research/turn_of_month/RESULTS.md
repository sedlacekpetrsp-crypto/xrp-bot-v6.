# Turn-of-month BTC/ETH — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (poslední 2 + první 3 dny měsíce).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | NE |
| 4_validation_x1_net_without_top3_gt_0 | NE |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold (koš 2 × 50 %)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 24162.61 | 241.6 | 1.91 | 25.7 | 54 | 2.97 | 61 | 11845.93 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | 22105.64 | 221.1 | 1.82 | 26.8 | 54 | 2.78 | 59 | 10235.23 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | 20172.51 | 201.7 | 1.74 | 28.2 | 54 | 2.60 | 57 | 8733.49 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | -3262.70 | -32.6 | -1.08 | 36.6 | 46 | 0.41 | 35 | -4426.46 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | -3609.84 | -36.1 | -1.23 | 37.7 | 46 | 0.37 | 33 | -4706.95 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | -3939.09 | -39.4 | -1.38 | 39.4 | 46 | 0.32 | 30 | -4974.96 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | -1256.34 | -12.6 | -0.21 | 24.1 | 42 | 0.75 | 57 | -2451.70 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | -1668.62 | -16.7 | -0.33 | 26.8 | 42 | 0.67 | 57 | -2803.39 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | -2061.47 | -20.6 | -0.45 | 29.4 | 42 | 0.60 | 55 | -3138.01 | -25.3 | -0.04 | 60.0 |

## Placebo (validace ×1, jen informace)

ToM je 28. z 28 posunutých 5denních oken podle čistého P/L; kladných placebo oken: 21 z 27.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
