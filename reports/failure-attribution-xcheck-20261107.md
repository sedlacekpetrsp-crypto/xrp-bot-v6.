# Nezávislý křížový přepočet C krok 0 (atribuce selhání) — 2026-11-07

Autopilot běh #33. Výhradně PAPER, jen čtení hotových `results.json` + `trades.csv` z větví R-série (PR #11–#32), žádná nová data, žádný backtest.
Účel: nezávislá kontrola závěru STOP 0 dialogové úlohy (`claude/maker-feasibility-step0-20261107`, `b88214f`, zpráva 0119/0120) jinou metodou.
Nástroj: `tools/research/failure_attribution.py` (konfigurace zvolených variant z protokolů). Strojový výstup: `reports/failure-attribution-xcheck-20261107.json`.

Metoda (protokol `research/maker_feasibility/PROTOCOL.md` krok 0, `de1088f`): validace 2023–24, náklady ×1, zvolená varianta. Hrubý = čistý + náklady (funding zůstává v hrubém).
(a) hrubý > 0 a hrubý bez 3 nejlepších > 0; (c) brány A1 (Sharpe i DD lepší než B&H, validace), A2 (≥ 30 obchodů) a A5 (závěrečný test čistý > 0, Sharpe i DD lepší než B&H) při nákladech **0,5×** — lineárně z hotových sloupců: X(0,5) = X(1) + 0,5·(X(1) − X(2)).
Kontrola ledgeru: součet `net_pnl` z trades.csv = `results.json` u 15/16 (výjimka `rsi2_cross_asset`: ledger je po aktivech s vlastním kapitálem, results.json je koš ⇒ ne chyba, jen jiná báze).

| Hypotéza | PR | Obch. | Hrubý ×1 | Náklady ×1 | % hrubého | Hrubý bez top 3 | Sharpe val. 0,5× / B&H | DD val. 0,5× / B&H | Závěr. čistý 0,5× | (a) | A1 | A2 | A5 | Nákladově limitovaná? |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|:-:|:-:|:-:|:-:|---|
| `donchian_trend` | #11 | 49 | 16 615 | 381 | 2,3 | 3 446 | 1,36 / 1,95 | 26,3 / 35,0 | -1 816 | ✔ | ✘ | ✔ | ✘ | NE — A1, A5 |
| `turn_of_month` | #12 | 46 | -2 865 | 398 | — | -4 057 | -1,00 / 1,71 | 36,0 / 34,0 | -1 050 | ✘ | ✘ | ✔ | ✘ | NE — hrubý/bez top 3, A1, A5 |
| `rsi2_pullback` | #13 | 51 | 2 692 | 569 | 21,1 | 1 431 | 0,67 / 1,71 | 16,9 / 34,0 | 1 676 | ✔ | ✘ | ✔ | ✔ | NE — A1 |
| `sma200_overlay` | #14 | 14 | 18 966 | 265 | 1,4 | 3 109 | 1,44 / 1,71 | 25,0 / 34,0 | -434 | ✔ | ✘ | ✘ | ✘ | NE — A1, A2, A5 |
| `vol_breakout` | #15 | 607 | 13 275 | 7 392 | 55,7 | 10 880 | 1,70 / 1,71 | 16,7 / 34,0 | -2 093 | ✔ | ✘ | ✔ | ✘ | NE — A1, A5 |
| `ts_momentum_vote` | #16 | 34 | 10 921 | 93 | 0,9 | 3 083 | 1,15 / 1,71 | 32,4 / 34,0 | -2 114 | ✔ | ✘ | ✔ | ✘ | NE — A1, A5 |
| `ethbtc_switch` | #17 | 71 | 20 755 | 2 350 | 11,3 | 5 584 | 1,40 / 1,71 | 28,6 / 34,0 | 4 221 | ✔ | ✘ | ✔ | ✔ | NE — A1 |
| `rebalance_band` | #18 | 8 | 30 385 | 67 | 0,2 | 6 778 | 1,65 / 1,71 | 35,5 / 34,0 | -2 189 | ✔ | ✘ | ✘ | ✘ | NE — A1, A2, A5 |
| `xrpbtc_switch` | #19 | 38 | 64 011 | 1 286 | 2,0 | 1 765 | 1,83 / 1,86 | 37,0 / 32,2 | -4 398 | ✔ | ✘ | ✔ | ✘ | NE — A1, A5 |
| `ethbtc_meanrev` | #20 | 56 | 37 137 | 1 750 | 4,7 | 16 444 | 1,68 / 1,71 | 39,0 / 34,0 | -4 093 | ✔ | ✘ | ✘ | ✘ | NE — A1, A2, A5 |
| `funding_carry` | #23 | 6 | 1 060 | 90 | 8,5 | 285 | 12,47 / 1,71 | 0,1 / 34,0 | 105 | ✔ | ✔ | ✘ | ✔ | NE — A2 |
| `rsi2_cross_asset` | #24 | 138 | 4 792 | 2 774 | 57,9 | 1 295 | 0,23 / 1,61 | 11,0 / 42,4 | 1 035 | ✔ | ✘ | ✔ | ✔ | NE — A1 |
| `vol_target` | #27 | 35 | 39 432 | 210 | 0,5 | 20 090 | 2,14 / 2,02 | 20,7 / 26,1 | -1 678 | ✔ | ✔ | ✔ | ✘ | NE — A5 |
| `near_high` | #28 | 72 | 28 013 | 383 | 1,4 | 4 223 | 1,45 / 1,49 | 32,0 / 40,5 | -2 584 | ✔ | ✘ | ✔ | ✘ | NE — A1, A5 |
| `contrarian_ladder` | #31 | 66 | 22 805 | 85 | 0,4 | 14 500 | 1,49 / 1,49 | 34,9 / 40,5 | -3 670 | ✔ | ✔ | ✔ | ✘ | NE — A5 |
| `bab_beta` | #32 | 312 | 1 521 | 772 | 50,7 | -1 133 | 0,44 / 1,73 | 13,9 / 37,2 | 668 | ✘ | ✘ | ✔ | ✔ | NE — hrubý/bez top 3, A1 |

**Výsledek: nákladově limitovaných hypotéz 0 z 16 ⇒ STOP 0 potvrzen** (shoda s `b88214f`).

Nejblíž hranici (pro evidenci, nic se neladí):
- `vol_breakout` (#15): náklady = 56 % hrubého, Sharpe validace při 0,5× ≈ 1,70 = B&H 1,71 (o 0,001 horší), ale závěrečný test i při 0,5× −2 093 USD ⇒ selhání signálu mimo vzorek, ne jen nákladů.
- `vol_target` (#27), `contrarian_ladder` (#31): A1 při 0,5× splněno, náklady < 1 % hrubého; padají na závěrečném testu (A5) — levnější exekuce nepomůže.
- `funding_carry` (#23): vše kromě A2 (6 epizod) ⇒ malý vzorek, ne náklady.
- `bab_beta` (#32), `rsi2_cross_asset` (#24): náklady 51–58 % hrubého, ale A1 daleko (Sharpe 0,44 / 0,23 vs B&H 1,73 / 1,61); BAB bez top 3 hrubě záporné.

Omezení: lineární extrapolace Sharpe/DD z ×1/×2 je aproximace; R12/R13 (backtest 2026-11-08) zatím nezahrnuty — doplnit stejným nástrojem. Závěr je screening (viz ChatGPT 0120 bod 4), ne důkaz nemožnosti maker hrany.
