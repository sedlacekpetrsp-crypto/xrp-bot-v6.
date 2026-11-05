# Combined PAPER selection — historical replay (NEPROVEDENO)

Stav 2026-11-05: **backtest na tržních datech NEBYL spuštěn.** Síťová politika
cloudového prostředí odmítla připojení k `data.binance.vision` (HTTP 403 na
CONNECT). Zde je pouze zmrazený protokol, kód a syntetické testy mechaniky.
Syntetické testy nejsou důkazem ziskovosti.

## Co se testuje a proč

Běžící PAPER monitor `COMBINED_BEST_SIGNALS_V1` (od 2026-11-04) používá
`research.combined_best_signals_paper.select_candidates`: VMM_V1 (90d absolutní
momentum, inverzní 30d volatilita) + dodatečný filtr 30d momenta >= 3 %, denní
volatilita <= 8 %, top 2, max 10 % na aktivum, max 20 % celkem, stop 12 %.

- VMM_V1 sám **neprošel** předregistrovanými branami 2026-10-22 (2022 a 2025
  záporné, validační DD 15,108 % > 15 %).
- Dodatečné filtry byly napsány 2026-11-04, tedy **po** zveřejnění validačních
  let 2023–2026/09. Tato léta jsou pro novou variantu kontaminovaná.
- Varianta nemá v repozitáři žádný backtest.

## Zmrazený protokol (zapsán před jakýmkoli výsledkem této varianty)

Data: Binance Vision měsíční 1h spot archivy BTC/ETH/SOL/XRP USDT od 2020-09.
Archivy do 2026-09 musí mít SHA-256 shodné s manifestem v
`reference_vmm_20261022.json` (kopie výsledků větve
`volatility-managed-momentum-research-20261022`). Ponechávají se jen UTC dny
kompletní (24 svíček) u všech čtyř aktiv, nic se nedoplňuje.

1. **Kontrola reprodukce:** nezměněné pravidlo VMM_V1 musí reprodukovat uložené
   metriky (obchody, čisté P/L, PF, max DD; tolerance 1e-6) pro 2021, 2022,
   2023, 2024, 2025, 2026 leden–září při 1× a 2× nákladech. Jinak se varianta
   NEVYHODNOCUJE (`ABORTED_CONTROL_MISMATCH`).
2. **Náklady:** fee 0,095 % + skluz 0,02 % na stranu (shodně s PAPER modulem);
   stres 2× a 3× (fee i skluz). Spot LONG bez páky, funding neexistuje.
3. **Bloky:** vývoj 2021, 2022; kontaminovaná kontrola 2023, 2024, 2025,
   2026/01–09 (+ souvislý 2023–2026/09); **čistá data** od 2026-10-01 do `--end`.
4. **Metriky:** počet obchodů (legů), win rate, čisté P/L, výnos, PF, max propad
   (hodinově oceněný), poplatky, čisté P/L bez 3 nejlepších obchodů, důvody výstupu.
5. **Historická podpora** (nutná, nikoli postačující): 2021 i 2022 kladné při 1×;
   souvislá 2023–2026/09 PF >= 1,25 při 1×, >= 1,10 při 2×, kladné P/L při 3×;
   max DD <= 15 %; >= 3/4 kontaminovaných bloků kladných při 1×; P/L bez 3
   nejlepších obchodů > 0.
6. **Žádné povýšení** ani změna rizika na základě historie: i při splnění bodu 5
   je třeba >= 30 nových legů na čistých datech (replay od 2026-10 + PAPER) s
   kladným P/L při 1× i 2×. Při <= 2 legech měsíčně to znamená >= 15 měsíců.
   Výsledek za 2026-10 (1 rebalance) bude **neprůkazný** a tak musí být označen.
7. Žádné ladění parametrů po zobrazení výsledků. Nevyhovující varianta se
   neinvertuje ani nezachraňuje filtrem na stejných letech.

## Spuštění po zpřístupnění dat

Potřebný přístup: HTTPS na `data.binance.vision` (pouze čtení, bez klíčů).

```sh
pip install -r requirements-dev.txt
python -m pytest -q tests/test_combined_selection_replay.py     # mechanika
python -m research.combined_selection_replay.run \
    --cache /tmp/vision-1h --end 2026-11-01 \
    --out research/combined_selection_replay/results.json
```

Exit code 0 = vyhodnoceno, 2 = neshoda kontroly (výsledky varianty se netvoří).
Výsledný JSON obsahuje manifest se SHA-256 všech archivů, včetně nových měsíců
2026-10+, které nejsou v referenčním manifestu (`in_reference_manifest=false`).

## Známé rozdíly replay vs. živý PAPER monitor

- Stop: replay hodinové low (fill na stopu, gap fill na horším open); PAPER
  kontroluje ticker každých ~15 min a plní na pozorované ceně.
- PAPER otevřel první pozice uprostřed měsíce (spuštění 2026-11-04); replay jen
  na začátku měsíce.
- PAPER denní svíčky z `1d` klines; replay agreguje kompletní hodinové dny.
- Rebalance timing byl v PAPER o den pozdě; opraveno v této větvi (není nasazeno).
