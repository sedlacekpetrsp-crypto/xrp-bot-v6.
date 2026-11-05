# SMA200 risk-off overlay na buy & hold BTC/ETH (denně) — předem registrovaný protokol (2026-11-05)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním výsledkem. Po prvním spuštění se pravidla,
dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších hypotéz (`reports/hypothesis-inventory-20261105.md` — žádný dlouhodobý
režimový filtr typu „cena vs. SMA200“ na držení spotu), od Donchian 20/55 (PR #11: vstup na průraz
N-denního maxima, výstup na průraz minima, 4 aktiva) a od RSI(2) (PR #13: krátké pullbacky, nízká
expozice). Zde je strategie „většinou v trhu“ (B&H) a jen v dlouhodobém downtrendu drží hotovost.
Hypotéza: vypnutím expozice pod SMA200 se vyhne velké části medvědích trhů ⇒ lepší Sharpe a nižší
max. drawdown než B&H po nákladech.

## Data
- Binance Vision, spot, denní svíčky (`data/spot/monthly/klines/<SYM>/1d/`), veřejná, bez klíčů.
- BTCUSDT, ETHUSDT, 2020-01 … 2026-10. SHA-256 každého archivu do `data_source.json`.
- SMA200 se počítá z celé historie (zahřátí před 2020-09), obchoduje se jen uvnitř období.

## Pravidla (long-only, bez páky, JEDINÁ varianta — žádná mřížka, nic se neladí)
- Signál na close dne t: close > SMA200(close) ⇒ cílově v pozici; close ≤ SMA200 ⇒ cílově hotovost.
- Změna cílového stavu ⇒ nákup/prodej za **open t+1** × (1 ± skluz). Bez stopu, bez časového limitu.
- První den období: rozhoduje signál z close předchozího dne (pozice se otevře za open prvního dne,
  pokud byl předchozí close nad SMA200).
- Na konci období nucené uzavření za close posledního dne × (1 − skluz).
- Hotovost bez úroku. Koš = 2 nezávislé sleeves (BTC, ETH) po 50 % kapitálu, celá sleeve do pozice,
  výnos se reinvestuje. Poplatek z nominálu na každé straně.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu; citlivost ×1, ×2, ×3 (obojí násobeno).

## Dělení (chronologicky)
- Ladění (zde jen kontrola, nic se nevybírá): 2020-09-01 … 2022-12-31
- Validace: 2023-01-01 … 2024-12-31
- Závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, výsledek se nepoužije k žádné úpravě.

## Měřítko
Buy & hold téhož koše (2 × 50 %, nákup za open prvního dne období, stejné náklady na vstup i výstup).

## Kritéria (předem dané, beze změny proti PR #11–#13)
Kandidát na forward PAPER jen pokud platí **všechno**:
1. Validace, koš, náklady ×1: Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.
2. Validace: ≥ 30 obchodů v koši.
3. Validace, náklady ×2: profit factor > 1,2 a čistý zisk > 0.
4. Validace, náklady ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test, náklady ×2: čistý zisk > 0 **a** Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.

Jinak verdikt **zamítnuto**. I „kandidát“ znamená jen kandidát na forward PAPER, ne zisková strategie.
Poznámka předem: overlay mění stav zřídka, kritérium 2 (≥ 30 obchodů) může být limitující; zachováno
beze změny kvůli srovnatelnosti s předchozími testy.

## Doplňková informace (NENÍ kritérium, nic se podle ní nevybírá)
- Varianty SMA100, SMA150 a SMA200 s pásmem ±2 % (vstup nad SMA×1,02, výstup pod SMA×0,98) —
  jen validace ×1, v `trades.csv` označeno `variant`.
- Expozice (% dní v pozici) a průměrná délka obchodu.

## Výstupy
`trades.csv` (každý obchod všech období a nákladů, vč. informačních variant), `results.json`,
`RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`.
