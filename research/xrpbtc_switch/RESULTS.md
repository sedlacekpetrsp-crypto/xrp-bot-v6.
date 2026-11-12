# Přepínání BTC ↔ XRP podle trendu XRPBTC — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (XRPBTC close > SMA50 ⇒ XRP, jinak BTC; vždy investováno).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold koše BTC/XRP 50/50

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 8096.37 | 81.0 | 0.76 | 77.8 | 56 | 1.10 | 48 | -27434.15 | 15.2 | 31.0 | 0.57 | 78.6 |
| tuning | ×2 | 5909.42 | 59.1 | 0.71 | 79.4 | 56 | 1.08 | 48 | -28095.71 | 15.2 | 30.7 | 0.56 | 78.6 |
| tuning | ×3 | 3986.75 | 39.9 | 0.66 | 80.9 | 56 | 1.06 | 45 | -28566.59 | 15.2 | 30.4 | 0.56 | 78.6 |
| validation | ×1 | 62725.16 | 627.3 | 1.80 | 37.5 | 38 | 4.30 | 45 | 649.82 | 19.2 | 488.9 | 1.86 | 32.2 |
| validation | ×2 | 56638.82 | 566.4 | 1.73 | 38.7 | 38 | 3.99 | 42 | -468.78 | 19.2 | 487.5 | 1.85 | 32.2 |
| validation | ×3 | 51061.82 | 510.6 | 1.67 | 40.1 | 38 | 3.70 | 42 | -1485.75 | 19.2 | 486.2 | 1.85 | 32.2 |
| final_test | ×1 | -4727.61 | -47.3 | -0.29 | 73.9 | 58 | 0.69 | 43 | -10467.35 | 11.5 | -28.7 | -0.04 | 62.3 |
| final_test | ×2 | -5386.05 | -53.9 | -0.41 | 76.8 | 58 | 0.64 | 41 | -10930.69 | 11.5 | -28.8 | -0.04 | 62.3 |
| final_test | ×3 | -5962.27 | -59.6 | -0.53 | 79.3 | 58 | 0.60 | 41 | -11319.10 | 11.5 | -29.0 | -0.05 | 62.3 |

## Informačně: B&H jednotlivých aktiv (×1)

| období | BTC výnos % | BTC Sharpe | BTC DD % | XRP výnos % | XRP Sharpe | XRP DD % |
|---|---|---|---|---|---|---|
| tuning | 41.7 | 0.57 | 76.6 | 20.3 | 0.69 | 83.2 |
| validation | 464.4 | 2.02 | 26.2 | 513.4 | 1.41 | 48.8 |
| final_test | -17.3 | -0.03 | 53.0 | -40.1 | -0.00 | 72.0 |

Podíl času v XRP (×1): tuning 43 %, validation 32 %, final_test 32 %

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |
|---|---|---|---|---|---|
| SMA20 | 61428.37 | 1.81 | 47.4 | 71 | 2.38 |
| SMA100 | 68507.31 | 1.86 | 46.7 | 18 | 6.52 |

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
