# Návrhy hypotéz a oponentury (vstup od externího asistenta / vlastníka)

Autopilot tento soubor čte při každém běhu. Nové položky přidávejte **na konec**, každou jako samostatnou
sekci podle šablony níže. Autopilot u každé doplní řádek „Stav:“ (zařazeno do fronty / zamítnuto, proč /
už testováno jako …) a nikdy položky nemaže.

Pravidla: výhradně PAPER výzkum; návrh je jen podnět — o zařazení rozhoduje rámec
`automation/RESEARCH_FRAMEWORK.md` (protokol předem, náklady ×1/×2/×3, chronologické dělení, Deflated Sharpe).

## Šablona — hypotéza
```
## H-<YYYYMMDD>-<n>: <krátký název>
- Zdroj výhody (proč by to mělo fungovat a proč to ještě není arbitrované):
- Pravidla (vstup / výstup / velikost pozice, bez volitelných detailů):
- Parametry a max. mřížka (nejvýš 4 varianty):
- Aktiva a časový rámec:
- Data (musí být veřejná a zdarma, ideálně Binance Vision):
- Čím se liší od už testovaných (viz STRATEGY_REGISTRY.md):
- Očekávaný počet obchodů za rok:
- Hlavní riziko / proč to může selhat:
- Odkaz na literaturu nebo zdroj (pokud existuje):
```

## Šablona — oponentura
```
## R-<YYYYMMDD>-<n>: oponentura <PR #N / soubor>
- Co jsem zkontroloval:
- Podezření na chybu (konkrétní řádek / číslo / soubor):
- Jak to ověřit (konkrétní test nebo výpočet):
- Závažnost: vysoká / střední / nízká
```

---

---
# Podnět vlastníka 2026-11-06 (soubor CLAUDE_HYPOTEZY_20261106.md)

## H-20261106-1: Funding settlement pressure
- Zdroj výhody (proč by to mělo fungovat a proč to ještě není arbitrované): Kolem vypořádání funding mohou přeplněné perpetual pozice měnit expozici. Krátké časové okno, poplatky a riziko squeeze mohou bránit úplné arbitráži. Jde pouze o hypotézu.
- Pravidla (vstup / výstup / velikost pozice): Na každém doloženém funding settlementu vypočítej percentil poslední **před vstupem známé** funding sazby z předchozích 90 dní. Pokud je nad 90. percentilem a poslední známý perp-spot basis kladný, otevři PAPER short perpetual na otevření další 5m svíčky; pokud pod 10. percentilem a basis záporný, PAPER long. Exit po 60 minutách; bez překryvu pozic; 10 % PAPER kapitálu na aktivum bez páky. Funding cash flow započítej pouze při skutečném držení pozice přes settlement.
- Parametry a max. mřížka (nejvýš 4 varianty): percentily 90/10 nebo 95/5 × držení 60 nebo 120 minut = 4 varianty. Ostatní pevné.
- Aktiva a časový rámec: BTCUSDT, ETHUSDT, XRPUSDT USDT-M perpetual; 5m, skutečné historické časy funding vypořádání.
- Data (veřejná, zdarma, ideálně Binance Vision): spot a futures 5m klines, funding history a timestamp zveřejnění/použitelnosti funding sazby; pokud historicky známou sazbu nelze rekonstruovat, netestovat bez náhradního předem zdokumentovaného zdroje.
- Čím se liší od už testovaných (viz STRATEGY_REGISTRY.md): Událostně časovaný intradenní efekt; porovnat s `funding_reversal`, `eth_funding_extreme`, `spot_perp_carry`.
- Očekávaný počet obchodů za rok: předběžný odhad 10–150 na aktivum, nutno změřit.
- Hlavní riziko / proč to může selhat: Look-ahead u konečné funding sazby, nepřesné časování, spread a skluz, krátká životnost signálu.
- Odkaz na literaturu nebo zdroj (pokud existuje): https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- **Stav (Claude, ruční běh 2026-11-06 15:55 UTC): DUPLICITNÍ — netestováno, N +0.** Jádro (po vypořádání fundingu sazba pod 10. / nad 90. percentilem z předchozích 90 záznamů ⇒ obchod proti znaménku) je pravidlo zamítnutého `funding_reversal` (XRP, 321 OOS obchodů, PF 0,76, ×2 0,59, ladicí 2022 i všechny brány kromě počtu ✘) a `eth_funding_extreme` (ETH, proti znaménku po settlementu, ✘); basis filtr = pozorovatelná veličina zamítnutého `premium_recovery`. Rozdíly (obě strany, 60/120 min, BTC/ETH/XRP, perp místo spotu) jsou parametrické varianty téhož mechanismu na už opotřebovaných datech; protokol `funding_reversal` výslovně doporučil další varianty derivátového crowdingu na těchto obdobích netestovat. Podrobně `reports/claude-hypotheses-triage-20261106.md`. Znovuotevřít jen jako čistě forward PAPER (bez historického ladění), a to jen rozhodnutím vlastníka.

## H-20261106-2: Cross-sectional funding dispersion
- Zdroj výhody (proč by to mělo fungovat a proč to ještě není arbitrované): Extrémní relativní náklad držení perpetual pozic může signalizovat přeplněnost a následné rozdíly ve výnosech. Short squeeze a omezený kapitál brání snadné arbitráži; výhoda není prokázána.
- Pravidla (vstup / výstup / velikost pozice): Každé pondělí 00:00 UTC seřaď pevný koš podle průměrné již realizované funding sazby za posledních 7 dní. PAPER long dvě nejnižší a short dvě nejvyšší; 10 % kapitálu na každou nohu, 40 % gross, bez páky. Drž 7 dní a pak uzavři a přepočítej. Při delším držení ignoruj nové signály až do ukončení koše. Započítej skutečné funding platby a veškeré náklady.
- Parametry a max. mřížka (nejvýš 4 varianty): funding okno 7/14 dní × držení 7/14 dní = 4 varianty.
- Aktiva a časový rámec: pevný koš BTC, ETH, XRP, SOL, BNB, ADA, DOGE, LTC USDT-M perpetual; hodinové ceny a týdenní rozhodnutí; historickou dostupnost aktiv a delisting respektovat.
- Data (veřejná, zdarma, ideálně Binance Vision): historické funding platby a futures klines, listing/delisting, poplatky a skluz.
- Čím se liší od už testovaných (viz STRATEGY_REGISTRY.md): Ranking relativních funding nákladů v multi-asset long-short koši, nikoli cenová `cross_sectional_rotation` nebo spot-perp `spot_perp_carry`; ověřit překryv s `oi_crowding` a `funding_reversal`.
- Očekávaný počet obchodů za rok: přibližně 104–208 nohových vstupů, podle zvolené délky držení a dostupnosti aktiv.
- Hlavní riziko / proč to může selhat: Squeeze, faktorová expozice, survivorship bias, financování a obrat portfolia. Long-short není automaticky delta-neutrální.
- Odkaz na literaturu nebo zdroj (pokud existuje): https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- **Stav (Claude, ruční běh 2026-11-06 15:55 UTC): ZAŘAZENO DO FRONTY (R8), N +4.** Nový mechanismus (relativní pořadí fundingu napříč košem, long-short) — žádný překryv s `cross_sectional_rotation` (cena), `spot_perp_carry`/`funding_carry` (1 aktivum, delta-neutrální), `oi_crowding`/`funding_reversal` (1 aktivum, intradenně). Protokol `5a10f26` (před kódem i daty), kód + testy `175424a`, draft PR #29. Backtest 2026-11-07 UTC (denní limit 3 nových hypotéz na 2026-11-06 vyčerpán).

## H-20261106-3: Spot-led price discovery
- Zdroj výhody (proč by to mělo fungovat a proč to ještě není arbitrované): Agresivní spotové obchody mohou krátkodobě předbíhat přecenění perpetual futures kvůli segmentaci účastníků; tržní konkurence a transakční náklady efekt rychle eliminují.
- Pravidla (vstup / výstup / velikost pozice): Po uzavření 5m svíčky spočítej spot taker-buy podíl. Pokud >65 %, spot 5m výnos >+0,2 % a současný futures 5m výnos <+0,1 %, otevři PAPER long perpetual až na následující 5m svíčce. Pro short zrcadlově: podíl <35 %, spot výnos <-0,2 %, futures výnos >-0,1 %. Exit po 15 minutách; maximálně jedna pozice na aktivum, 10 % PAPER kapitálu bez páky.
- Parametry a max. mřížka (nejvýš 4 varianty): taker-buy podíl 65/35 nebo 70/30 × držení 15 nebo 30 minut = 4 varianty.
- Aktiva a časový rámec: BTCUSDT, ETHUSDT, XRPUSDT spot a USDT-M perpetual; 5m.
- Data (veřejná, zdarma, ideálně Binance Vision): spot klines s taker-buy base volume a futures klines, striktně synchronizované UTC časy; audit chybějících svíček.
- Čím se liší od už testovaných (viz STRATEGY_REGISTRY.md): Konkrétní spot-to-perp reakce s taker-buy filtrem; porovnat s `btc_lead_lag`, `large_trade_followthrough`, `flow_pressure` a `cross_exchange_residual`.
- Očekávaný počet obchodů za rok: hrubý odhad 20–300 na aktivum; změřit bez dodatečného ladění.
- Hlavní riziko / proč to může selhat: Falešný lead-lag kvůli nesynchronním datům, nemožná exekuce, round-trip náklady minimálně 0,23 % při ×1.
- Odkaz na literaturu nebo zdroj (pokud existuje): https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
- **Stav (Claude, ruční běh 2026-11-06 15:55 UTC): ZAŘAZENO DO FRONTY (R9, nízká priorita), N +4.** Částečný překryv: `flow_pressure` (taker-buy podíl XRP 15m, spot long, PF 0,82 ✘), `btc_lead_lag` (lead-lag mezi aktivy 1h ✘); nový prvek = nesoulad spot vs perp téhož aktiva, obchod na perpu, obě strany. Rámec v2 bod 5 dává přednost jiným zdrojům ⇒ až po R8. Protokol `883cf7d`, kód + testy `95d9cf9`, draft PR #30. Backtest 2026-11-07 UTC.
