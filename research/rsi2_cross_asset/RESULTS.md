# RSI(2) pullback — křížový test na 8 aktivech (protokol `PROTOCOL.md`)

**Koš, stopa B: ZAMÍTNUTO**

| kritérium (koš) | splněno |
|---|---|
| B1_validation_x2_net_gt_0_and_pf_gt_1_2 | NE |
| B2_dd_le_0_6_bh_validation_and_final | ano |
| B3_final_x2_net_gt_0 | ano |
| B4_validation_x1_without_top3_gt_0 | NE |
| B5_trades_validation_plus_final_ge_20 | ano |
| B6_tuning_x1_net_gt_0 | ano |

Aktiva přidaná do forward PAPER (pravidlo protokolu): **XRPUSDT, LTCUSDT**
Aktiva se ziskem ve validaci ×2 i závěrečném ×2: XRPUSDT, BNBUSDT, LTCUSDT

## Koš 8 × 12,5 % vs buy & hold

| období | náklady | výnos % | Sharpe | max DD % | obchody | PF | B&H výnos % | B&H DD % |
|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 39.6 | 0.50 | 29.6 | 126 | 1.32 | 551.0 | 84.1 |
| tuning | ×2 | 34.2 | 0.47 | 30.9 | 126 | 1.28 | 549.5 | 84.1 |
| tuning | ×3 | 28.9 | 0.43 | 32.2 | 126 | 1.24 | 548.0 | 84.1 |
| validation | ×1 | 2.5 | 0.16 | 11.4 | 138 | 1.07 | 452.0 | 42.4 |
| validation | ×2 | -1.6 | 0.02 | 12.3 | 138 | 0.96 | 450.7 | 42.4 |
| validation | ×3 | -5.5 | -0.12 | 13.1 | 138 | 0.85 | 449.5 | 42.4 |
| final_test | ×1 | 8.9 | 0.42 | 11.2 | 91 | 1.36 | -50.9 | 70.5 |
| final_test | ×2 | 6.0 | 0.31 | 11.9 | 91 | 1.23 | -51.0 | 70.5 |
| final_test | ×3 | 3.2 | 0.20 | 12.6 | 91 | 1.12 | -51.1 | 70.5 |

## Jednotlivá aktiva (náklady ×2)

| aktivum | validace % | DD % | B&H % | B&H DD % | závěr. % | DD % | B&H % | B&H DD % | obchody V+Z | do forwardu |
|---|---|---|---|---|---|---|---|---|---|---|
| SOLUSDT | 12.1 | 28.5 | 1790.1 | 44.9 | -8.6 | 17.4 | -49.8 | 76.3 | 36 | NE |
| XRPUSDT | 15.0 | 18.2 | 512.0 | 48.8 | 28.5 | 21.6 | -40.2 | 72.0 | 32 | ano |
| BNBUSDT | 4.4 | 25.6 | 183.8 | 41.0 | 27.9 | 8.0 | -0.2 | 58.2 | 41 | NE |
| ADAUSDT | -38.4 | 43.6 | 242.2 | 59.8 | -3.4 | 22.0 | -77.3 | 87.3 | 25 | NE |
| DOGEUSDT | 25.9 | 18.8 | 347.8 | 57.9 | -22.9 | 40.8 | -76.2 | 83.4 | 24 | NE |
| LINKUSDT | -23.5 | 33.9 | 257.3 | 56.3 | -5.2 | 20.1 | -42.0 | 73.1 | 20 | NE |
| LTCUSDT | 6.5 | 20.2 | 46.6 | 50.7 | 37.6 | 16.5 | -46.2 | 70.1 | 31 | ano |
| AVAXUSDT | -14.4 | 25.6 | 226.1 | 67.8 | -6.0 | 28.2 | -76.1 | 86.6 | 20 | NE |

Deflated Sharpe (koš, validace ×1, N = 13): `{"sharpe_per_period": 0.008265045038780294, "skew": 0.3770442280019773, "kurtosis": 30.382636489216605, "T": 731, "n_trials": 13, "var_trials": 0.0013679890560875513, "sr0": 0.06300006701889391, "psr_vs_0": 0.5884663852491794, "dsr": 0.06933048553558852}`

Výsledek je post-hoc vůči RSI(2) na BTC/ETH (PR #13). Výhradně PAPER výzkum — ani „prošlo“ neznamená ziskovou strategii.
