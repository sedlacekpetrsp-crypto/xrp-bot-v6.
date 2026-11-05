# Hlasování časového momenta 1/3/6/12 měsíců, BTC/ETH — předem registrovaný protokol (2026-11-05)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost: SMA200 overlay (PR #14) = binární signál z 1 horizontu, denní kontrola; `volatility_managed_momentum`
(inventář #101) = škálování expozice volatilitou. Zde **částečná expozice** 0/25/50/75/100 % podle počtu
kladných horizontů (hlasování), měsíční rebalance ⇒ hladší přechody mezi režimy.

## Data
- Binance Vision spot 1d klines BTCUSDT, ETHUSDT 2020-01 … 2026-10, SHA-256 archivů do `data_source.json`
  (stejný loader jako PR #14/#15).

## Pravidla (long-only, bez páky, JEDINÁ varianta)
- Signál k poslednímu dni měsíce M (close c(t)): r_h = c(t) / c(t − h) − 1 pro h ∈ {30, 91, 182, 365} kalendářních dní.
- Cílová expozice sleeve w = (počet r_h > 0) / 4 ∈ {0; 0,25; 0,5; 0,75; 1}.
- Rebalance za open prvního dne měsíce M+1 na cílovou váhu (z aktuální hodnoty sleeve); nakupovaná/prodávaná
  část platí poplatek + skluz. Mezi rebalancemi se váha nemění (drift ceny se nerebalancuje).
- Koš = 2 nezávislé sleeves (BTC, ETH) po 50 % kapitálu; hotovost bez úroku.
- „Obchod“ = každá rebalance sleeve se změnou cílové váhy ≠ 0 (záznam v `trades.csv`, net_pnl = realizovaný
  + nerealizovaný přírůstek hodnoty sleeve od předchozí změny po nákladech). Konec období = nucené uzavření.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
- Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31;
  závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje.

## Měřítko
Buy & hold téhož koše (2 × 50 %, nákup za open prvního dne období, stejné náklady).

## Kritéria (beze změny proti PR #11–#15)
1. Validace ×1: Sharpe > Sharpe B&H **a** max DD < max DD B&H.
2. Validace: ≥ 30 obchodů v koši (pozn.: max. 48 rebalancí; riziko nesplnění přiznáno předem, kritérium se nemění).
3. Validace ×2: PF > 1,2 a čistý zisk > 0.
4. Validace ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test ×2: čistý zisk > 0 **a** Sharpe > B&H **a** max DD < B&H.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER.

## Doplňková informace (není kritérium)
- Horizonty {30, 91, 182} dní; týdenní rebalance (pondělí) se 4 horizonty — jen validace ×1, `variant` v `trades.csv`.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`.
