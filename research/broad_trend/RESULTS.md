# A2 ŠIROKÝ TREND — výsledky (run 42555037140, protokol `b6445c5`, kód `25e8014`)

**Verdikt: ZAMÍTNUTO** (K4, K5, DSR 0,038, soused W100_LS záporný). Výhradně PAPER výzkum, žádná „zisková strategie“.

Data: Binance Vision USDT-M 1d klines 20 828 archivů (913 symbolů vč. delistovaných, 0 chybějících) + fundingRate
7 735 archivů (401 symbolů, které prošly PIT univerzem; 15 měsíců 404 — bez fundingu), SHA-256 = `.CHECKSUM` 28 563/28 563.
Nezávislý přepočet z `trades.csv.gz`: 72 skupin, 0 neshod.

## Výběr na ladění ×1 (Sharpe)
| varianta | ladění ×1 | validace ×2 | závěr ×2 |
|---|---|---|---|
| W50_LO | +57,5 %, Sh 0,99 | +22,5 %, Sh 0,72 | −13,0 % |
| W50_LS | +27,0 %, Sh 0,56 | −3,6 %, Sh 0,00 | −0,8 % |
| **W100_LO (zvolena)** | +63,5 %, Sh 1,11 | +16,4 %, Sh 0,57 | −21,4 % |
| W100_LS | +35,6 %, Sh 0,67 | −14,8 %, Sh −0,38 | −19,3 % |

## Zvolená W100_LO vs benchmarky
| blok | strategie ×2 | EXPOSURE-MATCHED ×2 | EW PIT koš ×1 | BTC B&H |
|---|---|---|---|---|
| ladění 2020-06…2022-09 | +61,3 %, Sh 1,08, DD 21,8 % | +55,5 %, Sh 0,98, DD 20,8 % | +66,7 %, Sh 0,74, DD 83,2 % | +89,5 %, Sh 0,74, DD 72,7 % |
| validace 2023-01…2024-09 | +16,4 %, Sh 0,57, DD 19,8 %, PF 1,39, 407 epizod | +14,8 %, Sh 0,51, DD 20,5 % | +59,7 %, Sh 0,74, DD 63,6 % | +282,6 %, Sh 1,83, DD 26,3 % |
| závěr 2025-01…2026-10 | −21,4 %, Sh −0,73, DD 25,4 % | −32,3 %, Sh −1,04, DD 34,9 % | −74,5 %, Sh −0,65, DD 79,4 % | −18,0 %, Sh −0,04, DD 53,0 % |

Průměrná hrubá expozice jen 0,20–0,25 (vol-target 40 %/n při σ altů 80–120 %). Funding ladění −2 403 (long platí), validace −436.
Likvidace 0; nucené výstupy (delist) ladění 12, závěr 45.

## Kritéria
- K1 ✅ validace ×2 +1 637 > EM +1 479, Sharpe 0,57 > 0,51 (rozdíl malý). K2 ✅ PF 1,39. K3 ✅ bez top 3 +983. K6 ✅ 407.
- K7 ✅ hrubý P/L ladění +8 996 = 42× náklad ×1 (215).
- **K4 ❌** stopa A: Sharpe 0,62 < BTC 1,83; stopa B: DD 19,5 % > 0,6 × 26,3 % (BTC).
- **K5 ❌** závěr ×2 −2 138 (< 0), i když lepší než EM (−3 229).
- **DSR 0,038** (N = 214) ❌; sousedé validace ×2: W50_LO +2 253, **W100_LS −1 485** ❌; walk-forward ×2 3/4 (2022 −1 705).

## Poznámky (informačně, post-hoc — nic se netestuje bez nové předregistrace)
- Trendový signál přidává k samotné nízké expozici jen málo (validace +0,06 Sharpe, závěr +0,31) — většina „řízení
  rizika“ je dána malou hrubou expozicí, ne časováním.
- LS varianty systematicky horší než LO a než EM ⇒ short trend altů na tomto koši hranu nemá.
