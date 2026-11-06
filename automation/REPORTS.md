# Reporty plánovaných běhů — nejnovější nahoře

Každý běh úlohy „XRP BOT – Automatický vývoj a kontrola“ sem přidá krátký report (3–6 řádků).
Výhradně PAPER.


## 2026-11-06 16:20 SEČ (běh #24)
- Nasazeno: `fd6065b` (PR #26, váš ruční deploy 14:18 SEČ) – PR #5 ano. Produkce v pořádku: 6× HTTP 200, 239 testů OK, 0 nových duplicit, nové epochy LH-WHALE a LIQUIDITY běží (0 obchodů, 10 000), P/L součet −3 144,10.
- Výzkum R5 **Blízkost ročnímu maximu, 8 aktiv** — připraveno ([PR #28](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/28)): protokol commitnut předem, kód + 13 testů OK. Backtest se spustí po půlnoci UTC (denní limit 3 nových hypotéz vyčerpán) — zatím žádná čísla.
- Anomálie: žádné; jen error logy Renderu nešly načíst (výpadek jejich log API, 503) — ověřím příště.
- DB 20,7 %. Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 14:30 SEČ (běh #23)
- Nasazeno: `083e7e7` (PR #25, váš ruční deploy 13:59 SEČ) – PR #5 ano. PR #26 (`fd6065b`) čeká na ruční deploy. Produkce v pořádku: 6× HTTP 200, pozastaveny WHALE/BEST-OF (+ FAST/FLY/LEADLAG/TV), 239 testů OK, 0 chyb, 0 nových duplicit, P/L součet −3 176,78.
- Výzkum R4: **Volatilitní cílení BTC 40 % — ZAMÍTNUTO** ([PR #27](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/27)). Poprvé splněna kritéria A1–A4: validace 2023–24 ×1 +392 % (Sharpe 2,14, DD 20,7 %, 35 úprav) vs buy & hold BTC +464 % (Sharpe 2,02, DD 26,2 %).
  Závěrečný test ×2 ale −17,4 % (Sharpe −0,09, DD 50,7 %) vs B&H −17,5 % (−0,03, 53 %) — v klesajícím trhu kopíruje B&H; DSR 0,64 < 0,95. Obchody přepočteny: 18 bloků, 0 neshod.
- DB 20,7 %. Další: blízkost ročnímu maximu, 8 aktiv (R5) — od zítřka (limit 3 nové hypotézy denně vyčerpán); forward RSI(2) startuje 7. 11.
- Od vás: po nasazení PR #26 nic dalšího; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 13:05 SEČ (ruční práce na žádost vlastníka)
- RSI(2) křížový test na 8 aktivech se stejnými pravidly ([PR #24](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/24)): **koš zamítnut** — validace ×2 −1,6 %, DSR 0,07 ⇒ RSI(2) nemá obecnou výhodu napříč aktivy. Pravidlo protokolu splnily XRP a LTC.
- Forward PAPER spuštěn: BTC, ETH (výjimka), XRP, LTC; start 2026-11-07, aktualizace při každém běhu autopilota, `research/forward/rsi2_pullback/STATUS.md`. Kontrola 16. 12., vyhodnocení po ≥ 30 obchodech.

## 2026-11-06 12:35 SEČ (běh #22)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, 238 testů OK, 0 chyb, 0 událostí, 0 nových duplicit, P/L součet −3 176,78).
- Výzkum R3: **Delta-neutrální funding carry BTC/ETH (spot long + perp short) — ZAMÍTNUTO** ([PR #23](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/23)).
  Validace 2023–24 ×2: +8,8 % s propadem jen 0,5 % (B&H +321 %, DD 34 %); závěrečný test ×2: +0,2 % (DD 0,3 %) vs B&H −21,9 %. DSR 1,00, walk-forward 3/4 let kladných.
  Neprošlo na počet obchodů (6 ve validaci, 11 celkem); navíc výnos 2025–26 byl pod úrokem z hotovosti ⇒ výhoda zmizela. Obchody přepočteny: 19 bloků, 0 neshod.
- Hotov i nástroj Deflated Sharpe (R2, [PR #22](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/22)). Data: perp svíčka 2026-10-28 na Binance Vision chybí ⇒ závěrečný test do 27. 10.
- DB 20,6 %. Další: volatilitní cílení BTC 40 % (R4).
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 10:35 SEČ (běh #21)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, 238 testů OK, 0 chyb, 0 událostí, 0 nových duplicit, P/L součet −3 176,78).
- Výzkum (rámec v2, R1): **přehodnocení 10 dosavadních hypotéz stopou B „řízené riziko“ — 0 z 10 prošlo** ([PR #21](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/21)).
  Nejblíž RSI(2) pullback: validace ×2 +1 414 USD (PF 1,38, DD 17 % vs B&H 34 %), závěrečný test ×2 +11,5 % (DD 6 %) vs B&H −25,1 % (DD 60 %) — ale v ladění 2020–22 −0,5 % ⇒ podmínka B6 nesplněna, není kandidát. Ostatní mají propad blízko trhu. Vstupy přepočteny z trades.csv: 90 bloků, 0 neshod.
- DB 20,5 %. Další: Deflated Sharpe nástroj (R2), pak funding carry BTC/ETH (R3).
- Od vás: jen pokud chcete RSI(2) přesto sledovat ve forward PAPER jako výjimku (post-hoc, B6 nesplněno) — jinak nic; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 08:15 SEČ (běh #20)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, testy OK, 0 chyb, 0 nových duplicit, BEST-OF +1 obchod, P/L součet −3 176,78).
- Výzkum: **Návrat poměru ETHBTC k průměru (z-skóre ±2, koš BTC/ETH) — ZAMÍTNUTO** ([PR #20](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/20)).
  Validace 2023–24 ×1: +354 % (Sharpe 1,65, DD 39 %, 28 obchodů) vs buy & hold 50/50 +321 % (Sharpe 1,71, DD 34 %) — vyšší zisk, ale horší riziko.
  Závěrečný test ×2: −45,9 % vs B&H −25,1 %. Obchody přepočteny: 11 bloků, 0 neshod.
- Fronta byla prázdná ⇒ doplněny 3 nové hypotézy: volatilitní cílení BTC (protokol commitnut), kontrariánský žebřík BTC, blízkost ročnímu maximu (8 aktiv).
- DB 20,5 %. Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 06:15 SEČ (běh #19)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, 238 testů OK, 0 chyb, 0 nových duplicit, P/L součet −3 176,32).
- Výzkum: **Přepínání XRP ↔ BTC podle trendu XRPBTC (SMA50) — ZAMÍTNUTO** ([PR #19](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/19)).
  Validace 2023–24 ×1: +627 % (Sharpe 1,80, DD 37,5 %, 38 obchodů) vs buy & hold 50/50 XRP/BTC +489 % (Sharpe 1,86, DD 32,2 %); bez 3 nejlepších obchodů (×2) ztráta.
  Závěrečný test ×2: −53,9 % (DD 77 %) vs B&H −28,8 % (DD 62 %). Obchody přepočteny: 11 bloků, 0 neshod.
- DB 20,4 %. Další: mean-reversion poměru ETHBTC (z-skóre ±2, protokol už commitnut); pak fronta prázdná ⇒ doplním 3 nové hypotézy.
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 04:15 SEČ (běh #18)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, testy OK, 0 chyb, 0 nových duplicit, P/L součet −3 176,32).
- Výzkum: **Pásmový rebalance koše BTC/ETH 50/50 ±5 p. b. — ZAMÍTNUTO** ([PR #18](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/18)).
  Validace 2023–24 ×1: +303 % (Sharpe 1,64, DD 35,5 %, jen 3 rebalance) vs buy & hold 50/50 bez rebalance +321 % (Sharpe 1,71, DD 34 %).
  Závěrečný test ×2: −22,3 % vs B&H −25,1 % (DD obě 60 %) ⇒ rebalance přidá jen ±1–8 %, žádná hrana. Obchody přepočteny: 11 bloků, 0 neshod.
- DB 20,3 %. Další: přepínání XRP ↔ BTC podle trendu XRPBTC (protokol už commitnut).
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 02:15 SEČ (běh #17)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, testy OK, 0 chyb, 0 nových duplicit, P/L součet −3 176,32).
- Výzkum: **Přepínání BTC ↔ ETH podle trendu ETHBTC (SMA50) — ZAMÍTNUTO** ([PR #17](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/17)).
  Validace 2023–24 ×1: +184 % (Sharpe 1,32, DD 30 %, 71 obchodů) vs buy & hold 50/50 +321 % (Sharpe 1,71, DD 34 %).
  Závěrečný test ×2: +31,5 % vs B&H −25,1 %, ale DD 60,7 % ≈ B&H a bez 3 nejlepších obchodů ztráta ⇒ zisk stojí na 2 úsecích. Obchody přepočteny: 11 bloků, 0 neshod.
- DB 20,2 %. Fronta doplněna o 3 nové hypotézy; další: pásmový rebalance 50/50 ±5 p. b. (protokol už commitnut).
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-06 00:10 SEČ (běh #16)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, testy OK, 0 chyb, 0 nových duplicit, P/L součet −3 166,91).
- Výzkum: **Hlasování časového momenta 1/3/6/12 m BTC/ETH — ZAMÍTNUTO** ([PR #16](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/16)).
  Validace 2023–24 ×1: +108 % (Sharpe 1,14, DD 32 %, 34 obchodů) vs buy & hold +321 % (Sharpe 1,71, DD 34 %).
  Závěrečný test ×2: −22,0 % (DD 33 %) vs B&H −25,1 % (DD 60 %) ⇒ chrání před propadem, ale není ziskový. Obchody přepočteny: 11 bloků, 0 neshod.
- DB 20,2 %. Další: přepínání BTC ↔ ETH podle trendu ETHBTC (protokol už commitnut).
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-05 22:15 SEČ (běh #15)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, 238 testů OK, 0 chyb, 0 nových duplicit, P/L součet −3 166,91).
- Výzkum: **Denní volatilitní průraz k=0,5 BTC/ETH — ZAMÍTNUTO** ([PR #15](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/15)).
  Validace 2023–24 ×1: +58,8 % (Sharpe 1,02, DD 24 %, 607 obchodů) vs buy & hold +321 % (Sharpe 1,71, DD 34 %); při nákladech ×2 už −21 % (PF 0,91).
  Závěrečný test ×2: −66 % vs B&H −25 % ⇒ náklady sežerou hranu. Obchody přepočteny: 9 bloků, 0 neshod.
- DB 20,1 %. Další: hlasování časového momenta 1/3/6/12 m (protokol už commitnut).
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-05 20:20 SEČ (běh #14)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, 0 chyb, 0 nových duplicit, P/L součet −3 197,26).
- Výzkum: **SMA200 risk-off overlay BTC/ETH — ZAMÍTNUTO** ([PR #14](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/14)).
  Validace 2023–24 ×1: +187 % (Sharpe 1,43, DD 25 %, jen 14 obchodů) vs buy & hold +321 % (Sharpe 1,71, DD 34 %).
  Závěrečný test ×2: −7,2 % (DD 30 %) vs B&H −25 % (DD 60 %) ⇒ chrání před propadem, ale není ziskový. Obchody přepočteny: 12 bloků, 0 neshod.
- DB 20,0 %. Fronta doplněna o 3 nové hypotézy; další: denní volatilitní průraz (protokol už commitnut).
- Od vás nic nového; PR #8/#9/#10 dál čekají na review.

## 2026-11-05 18:20 SEČ (běh #13)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny (6× HTTP 200, 0 chyb, 0 nových duplicit, P/L součet −3 197,26).
- Výzkum: **RSI(2) pullback v uptrendu BTC/ETH — ZAMÍTNUTO** ([PR #13](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/13)).
  Validace 2023–24: +21 % po nákladech ×1, +14 % ×2 (Sharpe 0,59, PF 1,38) vs buy & hold +321 % (Sharpe 1,71) ⇒ nesplněno kritérium 1.
  Závěrečný test ×2: +11,5 % (DD 6 %) vs B&H −25 %; ladění 2020–22 ≈ 0 % ⇒ nestabilní, jen informace.
- Obchody nezávisle přepočteny: 12 bloků, 0 neshod. DB 19,9 %.
- Od vás nic nového; PR #8/#9/#10 dál čekají na review. Další: SMA200 risk-off overlay.

## 2026-11-05 16:03 SEČ (běh #12)
- Nasazeno: `edaa938` – PR #5 ano. Produkce beze změny, žádné nové chyby ani duplicity.
- Výzkum: **Turn-of-month BTC/ETH — ZAMÍTNUTO** ([PR #12](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/12)).
  Validace 2023–24: −33 % (Sharpe −1,08) vs buy & hold +321 % (1,71); závěrečný test ×2 náklady −17 % vs B&H −25 %.
  Placebo: ToM nejhorší z 28 posunutých oken ⇒ žádný efekt přelomu měsíce.
- Obchody nezávisle přepočteny: 9 bloků, 0 neshod.
- Další: RSI(2) pullback v uptrendu.

## 2026-11-05 14:40 SEČ (ruční běh)
- Výzkum: **Donchian trend 20/55 (BTC/ETH/SOL/XRP) — ZAMÍTNUTO** ([PR #11](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/11)).
  Validace ×1: +162 % (Sharpe 1,35) vs B&H +738 % (1,94); závěrečný test ×2: −21 % vs B&H −35 %.
- Obchody nezávisle přepočteny: 36 bloků, 0 neshod.

## 2026-11-05 dopoledne
- BEST-OF: oprava duplicitního zápisu + testy proti PostgreSQL ([PR #8](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/8), čeká na schválení),
  návrh výjimky pro id 129 ([PR #10](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/10)).
- Combined replay: export 300 obchodů ověřen ([PR #9](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/9)).
