# Pásmový rebalance koše BTC/ETH 50/50 (±5 p. b.) — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších: `weekly_inverse_vol_basket` (inventář #104) = váhy podle inverzní volatility, pevný týdenní
rozvrh; `volatility_managed_momentum` (#101) = škálování expozice; PR #11–#17 = časování trhu / relativní trend.
Zde **pevné váhy 50/50, vždy plně investováno, obchod jen při odchylce vah** ⇒ testuje se čistě „rebalancing premium“
(sklizeň mean-reversion poměru BTC/ETH) proti stejnému koši bez rebalance. Žádný signál z trendu ani volatility.

## Data
- Binance Vision spot 1d klines BTCUSDT, ETHUSDT 2020-01 … 2026-10, SHA-256 archivů do `data_source.json`.

## Pravidla (long-only, bez páky, JEDINÁ varianta)
- Start období: nákup 50 % BTC a 50 % ETH za open prvního dne (skluz + poplatek).
- Každý den k close: váha BTC w = hodnota BTC / hodnota koše. Pokud |w − 0,5| > 0,05, za open dalšího dne
  prodat přebytek jednoho aktiva a za výnos koupit druhé tak, aby váhy byly 50/50 (podle open cen).
- Konec období: prodej všeho za close (skluz + poplatek).
- „Obchod“ = úsek držení jedné sleeve (aktiva) mezi dvěma rebalancemi (resp. startem/koncem); net_pnl = změna hodnoty
  sleeve za úsek včetně nákladů, které ji v úseku zatížily ⇒ součet net = P/L strategie.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
- Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31;
  závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje.

## Měřítko
Buy & hold koše BTC/ETH 50/50 bez rebalance (nákup za open prvního dne, stejné náklady). Informačně BTC a ETH samostatně.

## Kritéria (beze změny proti PR #11–#17)
1. Validace ×1: Sharpe > Sharpe B&H 50/50 **a** max DD < max DD B&H 50/50.
2. Validace: ≥ 30 obchodů.
3. Validace ×2: PF > 1,2 a čistý zisk > 0.
4. Validace ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test ×2: čistý zisk > 0 **a** Sharpe > B&H 50/50 **a** max DD < B&H 50/50.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER.
Pozn.: předem se očekává, že kritéria 2 a 5 mohou selhat (málo rebalancí; v klesajícím trhu je koš záporný) —
výsledek se tím nemění, protokol zůstává.

## Doplňková informace (není kritérium, nic se nevybírá)
- Pásmo ±10 p. b. a pevný měsíční rebalance (1. den měsíce) — jen validace ×1, `variant` v `trades.csv`.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`.
