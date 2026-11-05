# Denní volatilitní průraz k=0,5 BTC/ETH — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (vstup open + 0,5 × včerejší rozpětí, výstup close téhož dne).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | NE |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold (koš 2 × 50 %)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 386.94 | 3.9 | 0.22 | 54.0 | 690 | 1.01 | 49 | -3880.66 | 0.0 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | -5350.41 | -53.5 | -0.73 | 72.8 | 690 | 0.89 | 45 | -8592.05 | 0.0 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | -7917.55 | -79.2 | -1.70 | 84.3 | 690 | 0.79 | 42 | -10605.06 | 0.0 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 5882.81 | 58.8 | 1.02 | 23.9 | 607 | 1.20 | 46 | 3533.07 | 0.0 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | -2099.01 | -21.0 | -0.34 | 38.4 | 607 | 0.91 | 40 | -3545.43 | 0.0 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | -6069.61 | -60.7 | -1.72 | 63.9 | 607 | 0.69 | 36 | -7147.79 | 0.0 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | -3605.18 | -36.1 | -0.69 | 39.5 | 557 | 0.83 | 40 | -5439.82 | 0.0 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | -6630.21 | -66.3 | -1.90 | 67.2 | 557 | 0.65 | 36 | -8020.54 | 0.0 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | -8224.28 | -82.2 | -3.09 | 82.6 | 557 | 0.52 | 32 | -9413.16 | 0.0 | -25.3 | -0.04 | 60.0 |

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |
|---|---|---|---|---|---|
| k03 | 558.48 | 0.25 | 34.2 | 884 | 1.01 |
| k07 | 2999.22 | 0.71 | 21.7 | 462 | 1.16 |
| k05_sma200 | 6207.05 | 1.21 | 13.8 | 464 | 1.30 |
| trade_day_share_pct | 41.52 | | | | |
| avg_net_bps_per_trade | 17.62 | | | | |

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
