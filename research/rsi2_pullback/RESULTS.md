# RSI(2) pullback v uptrendu BTC/ETH — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (close > SMA200, RSI2 < 10, výstup close > SMA5).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | ano |

## Strategie vs. buy & hold (koš 2 × 50 %)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | -46.94 | -0.5 | 0.14 | 34.8 | 31 | 0.99 | 65 | -2125.68 | 4.0 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | -395.78 | -4.0 | 0.09 | 34.9 | 31 | 0.92 | 65 | -2400.58 | 4.0 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | -732.08 | -7.3 | 0.04 | 35.1 | 31 | 0.86 | 65 | -2673.07 | 4.0 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 2122.63 | 21.2 | 0.59 | 17.1 | 51 | 1.59 | 67 | 898.77 | 3.8 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | 1414.29 | 14.1 | 0.44 | 17.5 | 51 | 1.38 | 67 | 283.96 | 3.8 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | 748.02 | 7.5 | 0.28 | 17.9 | 51 | 1.20 | 67 | -294.44 | 3.8 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | 1501.76 | 15.0 | 0.70 | 5.9 | 27 | 2.58 | 67 | 339.55 | 3.3 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | 1153.75 | 11.5 | 0.56 | 6.0 | 27 | 2.09 | 59 | 41.73 | 3.3 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | 816.40 | 8.2 | 0.41 | 6.5 | 27 | 1.69 | 52 | -246.24 | 3.3 | -25.3 | -0.04 | 60.0 |

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |
|---|---|---|---|---|---|
| rsi_lt5 | 1453.38 | 0.65 | 7.3 | 21 | 2.68 |
| rsi_lt15 | 963.00 | 0.32 | 20.4 | 69 | 1.19 |
| no_sma200 | 3440.14 | 0.75 | 22.6 | 71 | 1.74 |

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
