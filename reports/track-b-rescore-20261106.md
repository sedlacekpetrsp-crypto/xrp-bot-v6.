# Přehodnocení 10 hypotéz (PR #11–#20) stopou B — 2026-11-06 (R1 fronty v2)

Výhradně PAPER. **Post-hoc**: kritéria stopy B vznikla po zveřejnění výsledků, proto by případné „prošlo“
smělo jít jen do forward PAPER (rámec v2, bod 3). Žádný nový backtest — čte se jen `results.json`
z výzkumných větví (commit v tabulce). Nástroj `tools/research/track_b_rescore.py` + `tests/test_track_b_rescore.py`.

Kritéria (`automation/RESEARCH_FRAMEWORK.md` bod 1, stopa B): B1 validace ×2 zisk > 0 a PF > 1,2;
B2 max DD ≤ 0,6 × DD B&H ve validaci i v závěrečném testu (oba při ×1); B3 závěrečný test ×2 zisk > 0;
B4 validace ×1 bez 3 nejlepších obchodů > 0; B5 validace + závěrečný test ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
Měřítko B&H = stejné jako v protokolu dané hypotézy (u párů/košů B&H 50/50 bez rebalance).
Hodnoty v USD na účet 10 000 (B1, B4, B6), DD a výnos v %. Body 8 fronty v1 (combined replay) není hypotéza.

| # | hypotéza (PR, commit) | B1 val ×2 net / PF | B2 DD val / lim · fin / lim | B3 fin ×2 % | B4 val bez top3 | B5 obch. | B6 ladění ×1 net | výsledek |
|---|---|---|---|---|---|---|---|---|
| 1 | donchian_trend ([#11](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/11), `9150059`) | ✔ 15 511,9 / 2,93 | ✘ 26,6 / 21,0 · 37,5 / 38,2 | ✘ -21,1 | ✔ 3 096,0 | ✔ 93 | ✔ 98 233,0 | neprošlo (B2, B3) |
| 2 | turn_of_month ([#12](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/12), `57c7e49`) | ✘ -3 609,8 / 0,37 | ✘ 36,6 / 20,4 · 24,1 / 36,0 | ✘ -16,7 | ✘ -4 426,5 | ✔ 88 | ✔ 24 162,6 | neprošlo (B1, B2, B3, B4) |
| 3 | rsi2_pullback ([#13](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/13), `f776cc5`) | ✔ 1 414,3 / 1,38 | ✔ 17,1 / 20,4 · 5,9 / 36,0 | ✔ 11,5 | ✔ 898,8 | ✔ 78 | ✘ -46,9 | neprošlo (B6) |
| 4 | sma200_overlay ([#14](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/14), `f485401`) | ✔ 18 228,7 / 13,62 | ✘ 25,3 / 20,4 · 30,0 / 36,0 | ✘ -7,2 | ✔ 2 906,4 | ✔ 32 | ✔ 29 234,8 | neprošlo (B2, B3) |
| 5 | vol_breakout ([#15](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/15), `143edb8`) | ✘ -2 099,0 / 0,91 | ✘ 23,9 / 20,4 · 39,5 / 36,0 | ✘ -66,3 | ✔ 3 533,1 | ✔ 1164 | ✔ 386,9 | neprošlo (B1, B2, B3) |
| 6 | ts_momentum_vote ([#16](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/16), `c35bf0b`) | ✔ 10 671,8 / 2,46 | ✘ 32,4 / 20,4 · 33,0 / 36,0 | ✘ -22,0 | ✔ 3 007,0 | ✔ 58 | ✔ 28 450,2 | neprošlo (B2, B3) |
| 7 | ethbtc_switch ([#17](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/17), `ea76cdf`) | ✔ 14 125,3 / 1,51 | ✘ 30,3 / 20,4 · 59,3 / 36,0 | ✔ 31,5 | ✔ 3 358,8 | ✔ 94 | ✔ 11 584,8 | neprošlo (B2) |
| 8 | rebalance_band ([#18](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/18), `1274caf`) | ✔ 30 210,9 / 8,86 | ✘ 35,5 / 20,4 · 60,0 / 36,0 | ✘ -22,3 | ✔ 6 739,3 | ✔ 24 | ✔ 11 666,0 | neprošlo (B2, B3) |
| 9 | xrpbtc_switch ([#19](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/19), `90af87a`) | ✔ 56 638,8 / 3,99 | ✘ 37,5 / 19,3 · 73,9 / 37,4 | ✘ -53,9 | ✔ 649,8 | ✔ 96 | ✔ 8 096,4 | neprošlo (B2, B3) |
| 10 | ethbtc_meanrev ([#20](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/20), `e4ea6cc`) | ✔ 32 479,9 / 2,27 | ✘ 39,2 / 20,4 · 61,0 / 36,0 | ✘ -45,9 | ✔ 6 123,3 | ✔ 53 | ✔ 2 717,5 | neprošlo (B2, B3) |

## Výsledek: 0 z 10 prošlo stopou B ⇒ žádný kandidát na forward PAPER

- Nejblíž je **RSI(2) pullback** (#13): splňuje B1–B5 (DD 17 % vs B&H 34 %, závěrečný ×2 +11,5 % s DD 6 %),
  ale v ladicím období 2020–22 je na nule (−46,94 USD = −0,47 %, Sharpe 0,14, DD 34,8 %). B6 je předem dané
  pravidlo a hranice se nemá posouvat post-hoc ⇒ **neprošlo**. Pokud by vlastník chtěl výjimku, šlo by jen
  o forward PAPER s označením „post-hoc, B6 nesplněno“ — rozhodnutí vlastníka, sám to nezakládám.
- Ostatní časovací/overlay strategie (#14, #16) sníží DD jen na ~0,55–0,95× B&H, ne na 0,6× v obou obdobích,
  a v závěrečném testu po nákladech ×2 prodělávají. Párové strategie (#17–#20) mají DD jako trh.
- Závěr pro frontu: denní TA na BTC/ETH nedává ani „řízené riziko“; pokračovat zdroji, které v1 netestovala
  (R3 funding carry, R4 vol-target, R5 průřez 52t maximum).

## Nezávislé ověření vstupů z `trades.csv`
Pro hlavní variantu každé hypotézy přepočten součet `net_pnl` ve všech 9 blocích (3 období × 3 náklady)
a „bez top 3“ ve validaci ×1: **90 bloků, 0 neshod** (tolerance 0,05 USD). U #20 je „bez top 3“ definováno
přes epizody E/B (`run.py` ř. 259): součet epizod 25 146,35 − top 3 = 6 123,35 = `results.json`.

## Poznámky
- Deflated Sharpe (rámec bod 2) se počítá jen u „prošlo“ ⇒ teď není potřeba; nástroj je další položka (R2).
- Průběžný N (otestované varianty v1 + v2) se vede ve `STRATEGY_REGISTRY.md`; toto přehodnocení N nezvyšuje
  (žádná nová varianta, jen nové kritérium nad stejnými 10 hlavními variantami).
