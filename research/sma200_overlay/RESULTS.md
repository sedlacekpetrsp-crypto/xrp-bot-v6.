# SMA200 risk-off overlay BTC/ETH — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (close > SMA200 ⇒ držet, jinak hotovost; plnění open t+1).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | NE |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold (koš 2 × 50 %)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 29234.78 | 292.3 | 1.27 | 52.0 | 14 | 4.91 | 21 | -7476.40 | 61.8 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | 28742.72 | 287.4 | 1.26 | 52.2 | 14 | 4.70 | 21 | -7767.96 | 61.8 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | 28258.18 | 282.6 | 1.25 | 52.3 | 14 | 4.51 | 21 | -8053.20 | 61.8 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 18701.68 | 187.0 | 1.43 | 25.3 | 14 | 15.17 | 57 | 2906.41 | 80.4 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | 18228.71 | 182.3 | 1.41 | 25.9 | 14 | 13.62 | 57 | 2656.99 | 80.4 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | 17763.68 | 177.6 | 1.39 | 26.5 | 14 | 12.34 | 57 | 2412.00 | 80.4 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | -531.15 | -5.3 | 0.06 | 30.0 | 18 | 0.81 | 17 | -2784.96 | 32.0 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | -724.57 | -7.2 | 0.02 | 30.5 | 18 | 0.75 | 17 | -2921.36 | 32.0 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | -914.00 | -9.1 | -0.02 | 31.1 | 18 | 0.70 | 17 | -3054.99 | 32.0 | -25.3 | -0.04 | 60.0 |

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |
|---|---|---|---|---|---|
| sma100 | 13735.14 | 1.27 | 38.4 | 35 | 3.00 |
| sma150 | 20850.15 | 1.55 | 25.3 | 17 | 11.28 |
| sma200_band2 | 15694.78 | 1.30 | 31.1 | 9 | 8.05 |

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
