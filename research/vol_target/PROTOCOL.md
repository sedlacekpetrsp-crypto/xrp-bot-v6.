# Volatilitní cílení BTC (vol-target 40 %, long-only) — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost: nejde o časování podle trendu (PR #14 SMA200, PR #16 momentum vote) — expozice se řídí jen
realizovanou volatilitou (shlukování volatility), ne směrem ceny. `volatility_managed_momentum` (inventář #101)
kombinoval momentum signál s vol-škálováním; `weekly_inverse_vol_basket` (#104) vážil více aktiv mezi sebou.
Zde jedno aktivum, žádný směrový signál, žádná páka (váha ≤ 100 %), zbytek v hotovosti (úrok 0).

## Data
- Binance Vision spot 1d klines BTCUSDT 2020-01 … 2026-10, SHA-256 archivů do `data_source.json`.
- Chybějící den ⇒ běh skončí chybou (žádné doplňování).

## Pravidla (JEDINÁ varianta)
- σ(t) = výběrová směr. odchylka 30 denních log-výnosů close (okno končí close t) × √365.
- Cílová váha w*(t) = min(1, 0,40 / σ(t)).
- Úprava pozice za open(t+1) jen když |w*(t) − w(t)| > 0,10, kde w(t) = aktuální podíl BTC na hodnotě portfolia k close t;
  po úpravě váha = w*(t) (vyhodnoceno za open(t+1), náklady z obratu).
- Start období: nákup BTC na w* spočtenou k close dne před startem, za open prvního dne. Konec = prodej všeho za close.
- „Obchod“ = úsek mezi dvěma úpravami (ledger souvislý, součet net_pnl = celkový P/L); net_pnl úseku zahrnuje náklady
  úpravy, která úsek ukončuje (první úsek i počáteční nákup).

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu (z obratu), citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
- Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31;
  závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje.

## Měřítko
Buy & hold BTC (100 %, nákup za open prvního dne, stejné náklady).

## Kritéria (stejná logika jako PR #11–#20)
1. Validace ×1: Sharpe > Sharpe B&H BTC **a** max DD < max DD B&H BTC.
2. Validace: ≥ 30 obchodů (úseků).
3. Validace ×2: PF úseků > 1,2 a čistý zisk > 0.
4. Validace ×1: čistý zisk > 0 i bez 3 nejlepších úseků.
5. Závěrečný test ×2: čistý zisk > 0 **a** Sharpe > B&H BTC **a** max DD < B&H BTC.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER.

## Doplňková informace (není kritérium, nic se nevybírá)
- Cíl 30 % a 60 % místo 40 % — jen validace ×1; informačně stejné pravidlo na ETHUSDT (validace ×1) — nestahuje se nic navíc kromě ETHUSDT.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`.
