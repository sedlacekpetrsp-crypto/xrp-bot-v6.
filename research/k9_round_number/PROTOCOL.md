# K9 ROUND_NUMBER_STOP_CLUSTERING — protokol kroku 0 + fáze A (mechanismus)

Stav: **NAVRŽENO, zmrazeno před daty** (2026-11-16, Claude, dialog 0351, téma HUNT-12).
Žádná data se zatím nestahovala, žádný výnos se nepočítal. Výkonnostní fáze B NENÍ součástí tohoto protokolu.

## Hypotéza a mechanismus (kdo platí)
Stop-loss a take-profit příkazy retailu se shlukují na kulatých cenách (Osler 2003, FX; Urquhart 2017 a
Mbanga 2019 — shlukování cen BTC na kulatých číslech). Při prvním dotyku kulaté úrovně se spustí shluk
stop-příkazů (tržní taker objednávky) ⇒ krátkodobé pokračování pohybu za úroveň; platí ten, kdo má stop na
předvídatelném místě. Fáze B (výnos) má smysl jen tehdy, pokud fáze A prokáže samotnou stopu mechanismu.

## Novelty gate (RESEARCH_FRAMEWORK §6)
| Řádek | Odpověď |
|---|---|
| Testovaná rodina | grep `round|kulat|clustering|stop` v registru, inventáři (110), IDEAS, archivu STATE, `git branch -r`: 0 shod. Nejbližší: #69 large_trade_followthrough, #32 aggressor_sell_burst (spouštěč = velký obchod/objem, ne cenová úroveň), A4 Vortex (TA směr). |
| Rozdíl mechanismu | ANO — spouštěč je ex-ante známá cenová úroveň, ne indikátor ani objem. |
| Měřitelnost mechanismu | ANO, nepřímo: spuštěné stopy = taker objem. Binance Vision 1m klines obsahují `taker_buy_base_asset_volume` ⇒ přebytek taker objemu ve směru průrazu na kulaté vs. placebo úrovni. Přímá kniha stop-příkazů neexistuje (omezení). |
| PIT zdroj | Binance Vision UM `klines/1m` (měsíční ZIP + CHECKSUM SHA-256). Úrovně jsou deterministické ⇒ žádný look-ahead v definici události. |
| Instrument, likvidita | BTCUSDT, ETHUSDT, XRPUSDT USDT-M perp, 2020-01 až 2026-10. |
| All-in náklady | taker 0,05 %/stranu + skluz 0,02 %/stranu ⇒ ~0,14 % round trip (×1). |
| Filtr hrana ≥ 3× náklad | **NEJISTÉ** — FX literatura uvádí pokračování v řádu desítek bp; pro fázi B nutných ≥ 0,42 % průměrně (×1) ⇒ prior nízký. Proto napřed levná fáze A; bez GO ve fázi A žádný výkonnostní test. |
| Chronologické OOS | Vývoj 2020-01..2023-12, závěrečný úsek 2024-01..2026-10 (jen potvrzení fáze A). |
| Verdikt | GO jen pro krok 0 + fázi A (mikrostruktura, ne výnos). |

## Definice (zmrazené)
- Krok úrovně S: BTC 1 000 USDT, ETH 100 USDT, XRP 0,10 USDT. Kulatá úroveň L = k·S.
- Placebo úrovně: L = (k + 0,37)·S a (k + 0,73)·S (nesalientní posun; ne 0,5, protože „půlky“ jsou také kulaté).
- Dotyk (událost): minuta t, kdy `high_t ≥ L > high_{t-60..t-1}` (průraz nahoru) nebo `low_t ≤ L < low_{t-60..t-1}`
  (dolů), tj. první dotyk po ≥ 60 min bez dotyku. Úrovně, které minuta t přeskočí celé (open už za L), se počítají
  také (L mezi předchozí close a extrémem t). Jedna úroveň na minutu: nejbližší k close_{t-1}.
- Metrika M1 (objem): r = log(volume_t / medián(volume_{t-60..t-1})).
- Metrika M2 (směrovost): podíl taker objemu ve směru průrazu: buy_t/volume_t (nahoru) resp. 1 − buy_t/volume_t (dolů),
  minus stejný podíl jako medián t-60..t-1.
- Statistika: D1 = průměr r(kulaté) − průměr r(placebo); D2 obdobně pro M2. Stratifikace po aktivu, poté průměr
  vážený počtem událostí. 95% interval: blokový bootstrap přes kalendářní dny (10 000 replikací, seed 20261116).

## Brány
- **Krok 0 (data):** pro každý měsíc a aktivum ZIP + CHECKSUM, SHA-256 shoda 100 %, ≥ 99 % minut v měsíci; jinak
  měsíc vyloučit a vykázat; < 90 % měsíců ⇒ DATA NO-GO.
- **Fáze A GO** (jen vývojové období): D1 ≥ +0,10 (≈ +10 % objemu) a dolní mez 95% CI D1 > 0 **a** D2 > 0 s dolní mezí
  CI > 0; potvrzení v závěrečném úseku: D1 > 0 s dolní mezí CI > 0. Jinak **METHOD NO-GO** — K9 uzavřít, nehledat
  náhradní endpoint, nepřecházet na jiné kroky úrovní.
- Fáze B (výnos po průrazu, náklady ×1/×2/×3, DSR) se předregistruje samostatným dodatkem až po GO fáze A a
  oponentuře ChatGPT, a výkon se spustí jen v rozsahu OWNER_DECISIONS.

## Omezení
Taker objem je jen proxy spuštěných stopů (může jít o momentum tradery reagující na úroveň — pro fázi B ekonomicky
podobný důsledek, ale mechanismus nerozliší). Kroky S jsou jediná volba bez mřížky (N +1 pro fázi A).

## Dodatek 1 (2026-11-16, PŘED jakýmikoli daty; podle oponentury ChatGPT, dialog 0353)
Prahy D1 ≥ +0,10, placebo 0,37/0,73 ani endpointy se NEMĚNÍ. Doplňuje se jen:
1. **Expozice:** report povinně obsahuje počty kulaté vs placebo po aktivu × roku × hodině UTC a průměrnou úroveň
   (cenová proxy). Slouží jen k popisu nerovnováhy; placebo se podle ní nepřelaďuje ani nepřevažuje.
2. **Síla brány:** před výpočtem D se z POČTŮ událostí na den (vývojové období, bez hodnot metrik) spočte syntetická
   tabulka síly (efekt 0,10/0,15/0,20 × sd 0,5/1,0 × korelace v dni 0/0,3). Rozhodující buňka: efekt 0,20 (2× prah),
   sd 1,0, korelace 0,3. Síla < 0,80 ⇒ nesplněná brána = **INCONCLUSIVE (nízká síla)**, ne METHOD NO-GO; GO se
   tím nemění. Práh se při nízké síle nepřelaďuje.
3. **Repliky:** report `valid_reps / 10 000` pro D1/D2 obou období; podíl neplatných > 5 % ⇒ **INCONCLUSIVE**.
4. **Po aktivech:** vedle pooled D se reportuje D a 95% CI každého aktiva (stejné převzorkované dny); není to brána.
5. Krok 0 a fáze A jsou čistě mikrostruktura bez výnosu. Fáze B (náklady 0,05 % fee + 0,02 % slippage na stranu ⇒
   ~0,14 % round-trip, hurdle 3× ≈ 0,42 %) jen samostatným dodatkem a schválením vlastníka.
