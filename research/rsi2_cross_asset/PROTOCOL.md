# RSI(2) pullback — křížový test na dalších aktivech, předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním výsledkem. Navazuje na PR #13
(`research/rsi2_pullback/PROTOCOL.md`, BTC/ETH). Účel: ověřit, zda se pravidla RSI(2) osvědčí i mimo
BTC/ETH (robustnost napříč aktivy) a získat víc obchodů. Vlastník 2026-11-06 12:42: „Proveď vše.“

## Pravidla — PŘESNĚ jako PR #13, nic se nemění ani neladí
- Signál na close t: close > SMA200 **a** RSI(2, Wilder) < 10, bez otevřené pozice ⇒ nákup za open t+1 × (1 + skluz).
- Výstup: close > SMA5 ⇒ prodej za open t+1 × (1 − skluz). Bez stopu, bez časového limitu.
- Nucené uzavření na konci období za close × (1 − skluz). Long-only, bez páky.
- Poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1 / ×2 / ×3. Používá se přímo kód
  `research/rsi2_pullback/run.py` (funkce `simulate`, `buy_hold`, `metrics`), žádná kopie pravidel.

## Aktiva a data
- SOLUSDT, XRPUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, LINKUSDT, LTCUSDT, AVAXUSDT — seznam pevně daný předem,
  nikdo se nevyřazuje podle výsledku. Binance Vision spot 1d, 2020-01 … 2026-10 (od prvního dostupného
  měsíce), SHA-256 každého archivu do `data_source.json`. Chybějící archiv = měsíc bez dat, zapsat.
- Obchoduje se jen tam, kde je k dispozici SMA200 (u později listovaných aktiv začíná později).

## Období (stejná jako PR #13)
Ladění 2020-09-01 … 2022-12-31, validace 2023-01-01 … 2024-12-31, závěrečný test 2025-01-01 … 2026-10-31.

## Vyhodnocení
- Každé aktivum zvlášť (sleeve 10 000 USD) proti buy & hold téhož aktiva, a koš 8 × 12,5 %.
- **Přidání aktiva do forward PAPER** (předem dané): validace ×2 čistý zisk > 0 **a** závěrečný test ×2
  čistý zisk > 0 **a** max DD ≤ 0,6 × max DD B&H v obou obdobích.
- **Koš (rozhoduje o tom, zda je RSI(2) robustní napříč aktivy) — stopa B rámce v2:** validace ×2 zisk > 0
  a PF > 1,2; validace i závěrečný test DD ≤ 0,6 × B&H; závěrečný ×2 zisk > 0; validace ×1 bez top 3 > 0;
  ≥ 20 obchodů; ladění ×1 zisk > 0. Plus počet aktiv s kladným ziskem ve validaci ×2 i závěrečném ×2.
- Deflated Sharpe: N = 13 (11 dosavadních hypotéz s jednou variantou + RSI(2) PR #13 + tento test),
  `tools/research/deflated_sharpe.py`, denní výnosy koše ve validaci.
- Výsledek je v každém případě post-hoc vůči původnímu RSI(2) (víme, že na BTC/ETH neprošlo B6) — i
  „prošlo“ znamená jen zařazení do forward PAPER.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`.
