# Donchian trend — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — zvolená varianta `N20_k2` (výběr podle Sharpe koše na ladění, náklady ×1).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Zvolená varianta vs. buy & hold (koš 4 × 25 %)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | bez top 3 | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 98233.00 | 982.3 | 2.09 | 52.9 | 38 | 2.36 | -21696.48 | 86.7 | 0.77 | 90.0 |
| tuning | ×2 | 96193.80 | 961.9 | 2.08 | 53.5 | 38 | 2.33 | -22893.82 | 86.3 | 0.77 | 90.0 |
| tuning | ×3 | 94193.50 | 941.9 | 2.06 | 54.1 | 38 | 2.29 | -24058.04 | 85.8 | 0.77 | 90.0 |
| validation | ×1 | 16234.81 | 162.3 | 1.35 | 26.6 | 49 | 3.06 | 3095.97 | 737.7 | 1.94 | 34.9 |
| validation | ×2 | 15511.88 | 155.1 | 1.31 | 27.3 | 49 | 2.93 | 2654.38 | 735.7 | 1.94 | 34.9 |
| validation | ×3 | 14809.06 | 148.1 | 1.28 | 28.0 | 49 | 2.81 | 2226.54 | 733.8 | 1.94 | 34.9 |
| final_test | ×1 | -1913.40 | -19.1 | -0.36 | 37.5 | 44 | 0.61 | -3169.52 | -34.9 | -0.09 | 63.7 |
| final_test | ×2 | -2108.61 | -21.1 | -0.42 | 38.4 | 44 | 0.58 | -3335.73 | -35.0 | -0.09 | 63.7 |
| final_test | ×3 | -2299.10 | -23.0 | -0.47 | 39.3 | 44 | 0.55 | -3497.76 | -35.2 | -0.09 | 63.7 |

## Ladění (výběr varianty)

- `N20_k2`: Sharpe 2.093
- `N20_k3`: Sharpe 2.002
- `N55_k2`: Sharpe 1.687
- `N55_k3`: Sharpe 1.624

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
