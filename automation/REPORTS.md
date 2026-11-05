# Reporty plánovaných běhů — nejnovější nahoře

Každý běh úlohy „XRP BOT – Automatický vývoj a kontrola“ sem přidá krátký report (3–6 řádků).
Výhradně PAPER.

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
