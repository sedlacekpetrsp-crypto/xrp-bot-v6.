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

## Dodatek 2 — předregistrace fáze B (výnos) (2026-11-17, Claude; NAVRŽENO, PŘED výpočtem jakéhokoli výnosu)
Stav: **NAVRŽENO k oponentuře ChatGPT. Výkon NESPOUŠTĚT**, dokud (a) ChatGPT nepotvrdí/neupraví tento dodatek v dialogu,
(b) v `dialog/OWNER_DECISIONS.md` není řádek vlastníka „SCHVÁLENO: výkonnost K9“. Do té doby se z dat nepočítá žádný
výnos K9 (ani průzkumně). Jediná data použitá při psaní: ČASY událostí fáze A (`phaseA_events.csv.gz`, bez cen/výnosů)
pro počty obchodů a sílu (`phase_b_power.py` → `phaseB_power_table.json`, SHA-256 `997625a6…bcde2734f`).

1. **Obchod (pevně).** Událost = dotyk z fáze A (stejný detektor `events.py`, stejné úrovně S, stejné měsíce z manifestu
   kroku 0). Směr = směr průrazu (nahoru ⇒ long, dolů ⇒ short). Vstup = **open minuty t+1** (signál je znám až po close t;
   pohyb uvnitř minuty t se nezapočítává). Výstup = **close minuty t+H**. Žádný stop/TP, žádná páka v metrice (výnos na
   1 jednotku notional). Na jednom aktivu nejvýš 1 pozice: signál během otevřené pozice se ignoruje (stejné pravidlo
   zvlášť pro kulaté a zvlášť pro placebo „portfolio“). Chybějící minuta v okně ⇒ obchod neplatný, vykázat podíl (> 1 % ⇒ INCONCLUSIVE).
2. **Varianty:** H ∈ {15, 60} min — jediné 2 varianty (žádná mřížka úrovní, směrů, filtrů hodin). **DSR N = 162**
   (159 předchozích + K9 fáze A + 2 varianty H). V[SR] podle R10 jako předpoklad ⇒ DSR je podmíněné.
3. **Náklady:** taker 0,05 % + skluz 0,02 % na stranu ⇒ 0,14 % round trip (×1), ×2 = 0,28 %, ×3 = 0,42 %. Funding:
   obchod, jehož držení překročí 00/08/16 UTC, dostane konzervativní **nepříznivý** poplatek 0,03 % za každé překročení
   (= 3× základní sazba; skutečný funding se nestahuje — omezení). Funding se násobí stejným multiplikátorem nákladů.
4. **Vývoj → výběr H (jen 2020-01..2023-12).** Spočte se hrubý průměrný výnos/obchod G(H) a čistý ×1 pro obě H.
   **Ekonomická předbrána (RESEARCH_FRAMEWORK, hrana ≥ 3× náklad):** pokud max_H G_dev(H) < **0,42 %** ⇒
   **NO-GO (ekonomicky)**, závěrečný úsek se pro výnos **NEOTEVÍRÁ** a K9 se uzavírá bez dalších variant.
   Jinak H* = argmax čistého ×1 ve vývoji (při shodě kratší H). Výběr se zapíše a commitne **před** výpočtem závěru.
5. **Závěrečný úsek (2024-01..2026-10), H* jen jednou.** Primární endpoint E = průměrný čistý výnos/obchod ×1.
   GO (jen návrh forward PAPER, nikdy produkce) vyžaduje **všechny** body:
   a) E > 0 a dolní mez 95% CI > 0 (blokový bootstrap přes kalendářní dny, 10 000 replik, seed 20261117; `invalid_frac` > 5 % ⇒ INCONCLUSIVE);
   b) čistý průměr ×2 > 0 (bodově) a ×3 se vykáže;
   c) **placebo benchmark:** Δ = G(kulaté) − G(placebo) se stejnými pravidly > 0, dolní mez CI > 0 (stejné převzorkované dny);
   d) **náhodný vstup:** pro každý obchod 5 náhodných minut stejného aktiva, stejného dne a stejné UTC hodiny, stejný směr
      a H (seed 20261117); G(kulaté) − G(náhodné) > 0, dolní mez CI > 0;
   e) DSR (Sharpe denní řady PnL, stejný notional na obchod, aktiva sečtena, anualizace 365, N = 162) ≥ 0,95;
   f) stabilita: čistý ×1 > 0 bodově u ≥ 2 ze 3 aktiv a v ≥ 2 ze 3 kalendářních let závěru (2024, 2025, 2026-01..10);
   g) síla: v rozhodující buňce (efekt 0,14 % = 1× náklad, sd 0,8 % pro H=15 / 1,6 % pro H=60, ρ 0,3) ≥ 0,80 —
      podle přísnějšího čtení 0353/0358 je síla **předpoklad** GO (NaN/ < 0,80 ⇒ INCONCLUSIVE). Předpočteno z časů: síla
      ≥ 0,99 ve všech buňkách (n závěr H15 = 12 417, H60 = 11 653 neprekrývajících se obchodů na kulatých úrovních).
   Selže-li a) nebo c) ⇒ **NO-GO**; selže-li jen b), d), e) nebo f) ⇒ **NO-GO** (bez ladění); g) ⇒ INCONCLUSIVE.
6. **Povinný report (ne brána):** trades.csv (každý obchod: aktivum, čas, směr, vstup, výstup, hrubý, náklady, funding,
   čistý ×1/×2/×3), results.json, RESULTS.md; rozpad po aktivu × roku × směru × UTC hodině; max drawdown denní equity,
   expozice (podíl času v pozici), počet obchodů; **buy-and-hold** stejně vážený BTC/ETH/XRP za závěrečný úsek a
   long-only expozičně párovaný B&H (stejné minuty v pozici, vždy long). Nezávislý přepočet E, Δ a DSR z trades.csv mimo runner.
7. **Interpretace:** GO ⇒ pouze návrh forward PAPER ≥ 60–90 dní (samostatné schválení vlastníka), žádná produkční změna.
   Kladný výsledek NENÍ důkaz ziskovosti. Závěrečný úsek 2024–26 byl už jednou použit pro mechanismus (objem, ne výnos) —
   omezení se uvede. Prior zůstává nízký: 0,42 % hrubě za 15–60 min je na BTC/ETH výrazně nad typickou volatilitou
   průrazů; očekávaný výsledek je spíš NO-GO ekonomickou předbránou.
8. Žádné další varianty (jiné S, filtry objemu/hodin, maker vstupy, trailing stop) bez nové hypotézy a nového dodatku.
