# Reporty plánovaných běhů — nejnovější nahoře

Každý běh úlohy „XRP BOT – Automatický vývoj a kontrola“ sem přidá krátký report (3–6 řádků).
Výhradně PAPER.

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
