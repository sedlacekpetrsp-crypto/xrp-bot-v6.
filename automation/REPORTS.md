# Reporty plánovaných běhů — nejnovější nahoře

Každý běh úlohy „XRP BOT – Automatický vývoj a kontrola“ sem přidá krátký report (3–6 řádků).
Výhradně PAPER.

## 2026-11-08 20:45 SEČ (běh #37)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce bez odchylek: 6× HTTP 200, vše healthy (ELITE V18/V56 tick 20:03 SEČ), testy OK, 0 událostí, 0 chyb v logu, 0 nových duplicit, P/L −3 110,37.
- A1 NEW-LISTING DRIFT (short nově listovaných perpů 30–60 dní po listingu, 671 listingů 2020–26 vč. delistovaných, funding, likvidace, náklady ×1/×2/×3) – **ZAMÍTNUTO** ([PR #39](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/39)): validace 2023–24 ×2 +6,6 % (PF 1,22), ale Sharpe 0,37 vs buy & hold BTC 1,36; závěrečný test 2025–26 ×2 **−13,0 %**, zatímco prostý short BTC se stejným rozvrhem +2,6 %; DSR 0,01. Většina obchodů vyhrává, ale squeeze/likvidace (39 v posledním bloku) berou celou pozici. Přepočet z trades.csv – shoda.
- Výsledek poslán ChatGPT (dialog 0225, HUNT-02). Další: protokol A2 – široký trend na ≥ 40 perpech (PIT koš).
- DB 22,8 %. Od vás nic nepotřebuji.

## 2026-11-08 17:10 SEČ (běh #36)
- Nasazeno: `fd6065b` – PR #5 ano. Váš ruční redeploy v 12:21 SEČ vyřešil výpadek ELITE V18/V56 – oba zase běží (poslední tick 16:04 SEČ). Jinak bez odchylek: 6× HTTP 200, 239 testů OK, 0 chyb v logu, 0 nových duplicit, P/L −3 110,37.
- A1 krok 1 (inventura nově listovaných perpů, bez výpočtu výnosů) – **GO** ([PR #38](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/38)): v archivu Binance je 923 USDT perpů, z toho 167 už delistovaných. Pro test se hodí 682 listingů z let 2020–2026 (166 z nich delistovaných), každý rok aspoň 22. Všech 24 067 souborů prošlo kontrolou SHA-256.
- Zjištění: u 156 delistovaných symbolů archiv dál vytváří denní svíčky s nulovým objemem (FTT 4 roky). První verze inventury tím zkreslila počet delistingů (31 místo 167), opraveno dodatkem 1. Každý další test na širokém koši proto počítá jen dny s objemem > 0.
- Další krok: protokol backtestu A1 (short 30–180 dní po listingu, funding, nucené uzavření při delistingu, náklady ×1/×2/×3), commitnutý před stažením cen. Forward RSI(2): data do 7. 11., 0 obchodů.
- DB 22,6 %. Od vás nic nepotřebuji.

## 2026-11-08 12:20 SEČ (běh #35)
- ⚠️ **ELITE V18/V56 stojí od 04:06 SEČ**: Binance na chvíli neodpověděl (timeout), proces se podle návrhu trvale přepnul na Kraken a ELITE na Kraken datech padá (ValueError). Nemá otevřenou pozici, ztrácí se jen forward data. Ostatní boty běží na Kraken datech. Náprava: ruční restart/deploy služby (vrátí Binance) — jen vy.
- Nasazeno: `fd6065b` – PR #5 ano. Jinak beze změny: 6× HTTP 200, 239 testů OK, 0 událostí, 1 přechodná chyba v logu (Binance 500 o půlnoci), 0 nových duplicit, P/L součet −3 110,37.
- R12 MAX efekt ([PR #33](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/33)) **ZAMÍTNUTO**: validace 2023–24 po nákladech ×2 +12,8 % vs. buy & hold +471 %; závěrečný test 2025–26 +6,1 % vs. B&H −42,6 %, ale PF 1,09, bez 3 nejlepších obchodů ztráta, DSR 0,02. R13 průřezové momentum ([PR #35](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/35)) **ZAMÍTNUTO**: validace −9,5 %, závěr −18,2 %. Obojí přepočteno z trades.csv – shoda.
- Atribuce selhání doplněna ([PR #36](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/36)): 0 z 18 testů není limitováno náklady ⇒ téma C uzavřeno. Forward RSI(2): 1. den, 0 obchodů. Nové hypotézy nepřidávám (čeká na uvolnění bodu A).
- DB 22,4 %. Od vás: rozhodnout o restartu služby kvůli ELITE (případně o trvalé opravě návratu na Binance).

## 2026-11-07 12:35 SEČ (běh #33)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, 239 testů OK, 0 chyb v logu, 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Podle vašeho rozhodnutí (12:05) jsem nové hypotézy nepřidával. Místo toho jsem **nezávisle přepočítal atribuci selhání** (C krok 0) všech 16 dokončených testů R-série jen z hotových dat ([PR #36](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/36)): **0 z 16** by neprošlo ani při polovičních nákladech (maker) — padají na Sharpe vs. buy & hold nebo na závěrečném testu, ne na poplatcích. Shoda s dialogovou úlohou (STOP 0) ⇒ levnější exekuce žádný dosavadní test nezachrání.
- Nejblíž: denní volatilitní průraz (#15) — náklady sežerou 56 % hrubého zisku, ale závěrečný test 2025–26 je záporný i při polovičních nákladech.
- DB 21,6 %. Další běh 8. 11.: backtesty R12 a R13 + první data forward RSI(2). Od vás nic nového; PR #8/#9/#10 dál na review.

## 2026-11-07 10:15 SEČ (běh #32)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, 239 testů OK, 0 chyb v logu (log API opět funguje), 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Výzkum: denní limit 3 nových hypotéz je vyčerpán ⇒ připravil jsem R13 **průřezové momentum long-short (long 2 nejsilnější / short 2 nejslabší perpy, tržně neutrální, držení 28 dní)** ([PR #35](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/35)): protokol commitnut před kódem, kód + 13 testů mechaniky OK. Zatím žádná čísla — backtest poběží 8. 11. po R12. Očekávání nízké (malý koš, R5 naznačil slabé pořadí).
- DB 21,4 %. Další běh 8. 11.: backtesty R12 a R13, pak doplním frontu. Od vás: R8/R9 dál čekají na uvolnění; PR #8/#9/#10 na review; oprava flaky testu TV čeká na souhlas.

## 2026-11-07 08:45 SEČ (běh #31)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, testy OK, 0 událostí, 0 nových duplicit, P/L součet −3 144,10. Error logy tentokrát neověřeny (Render log API vrací 503) — zkusím příště.
- Výzkum: denní limit 3 nových hypotéz je vyčerpán ⇒ udělal jsem R10 **rekonstrukci počtu dosud zkoušených variant** ([PR #34](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/34)): doloženo **N = 190** (dosavadní odhad 159 byl nízký; 190 je jen dolní mez), rozptyl Sharpe pokusů 0,40.
- Dopad: práh pro Deflated Sharpe se posune jen nepatrně (potřebný Sharpe 3,07 → 3,11) ⇒ žádný dřívější verdikt se nemění. Od R12 počítám s N = 190.
- DB 21,4 %. Forward RSI(2) zatím bez dat (první svíčka 8. 11.). Další běh 8. 11.: backtest R12 MAX efekt, pak R13. Od vás: R8/R9 dál čekají na uvolnění; PR #8/#9/#10 na review.

## 2026-11-07 06:30 SEČ (běh #30)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, testy OK, 0 chyb, 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Výzkum R12 **MAX efekt (short 3 perpy s nejvyšším nedávným max. denním výnosem, long 3 s nejnižším, tržně neutrální)** — připraveno ([PR #33](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/33)): protokol commitnut před kódem, kód + 10 testů mechaniky OK. Zatím žádná čísla — denní limit 3 nových hypotéz je vyčerpán (R5, R7, R11); backtest poběží 8. 11.
- DB 21,3 %. Od vás: R8/R9 dál čekají na uvolnění; PR #8/#9/#10 na review; oprava flaky testu TV čeká na souhlas.

## 2026-11-07 04:25 SEČ (běh #29)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, testy OK, 0 chyb, 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Fronta byla prázdná ⇒ doplnil jsem 3 nové hypotézy (R11–R13, všechny **tržně neutrální long-short na perpech** — všech 7 long-only pokusů padlo na medvědím 2025–26).
- Výzkum R11 **Betting-against-beta (long 3 aktiva s nejnižší betou, short 3 s nejvyšší), 8 perpů** — **ZAMÍTNUTO** ([PR #32](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/32)): validace 2023–24 ×2 −0,0 % (×1 +7,5 %, DD 16 %) vs B&H koše +472 %; závěrečný test 2025–26 ×2 −3,0 % (DD 12 %) vs B&H −42,6 % (DD 65 %); DSR 0,01. Neutralita funguje (beta 0,05), ale hrana ~1–3 % ročně nepokryje náklady. Přepočet z trades.csv: 21 bloků, 0 neshod.
- DB 21,2 %. Další běh: R12 MAX efekt / R13 momentum long-short od 8. 11. (dnešní limit 3 hypotéz vyčerpán). Od vás: R8/R9 dál čekají na uvolnění; PR #8/#9/#10 na review; oprava flaky testu TV čeká na souhlas.

## 2026-11-07 02:20 SEČ (běh #28)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, 0 chyb, 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Výzkum R7 **Kontrariánský žebřík (50 % držet, 50 % dokupovat po třetinách při propadu 20/30/40 % pod ročním maximem), 8 aktiv** — **ZAMÍTNUTO** ([PR #31](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/31)): validace 2023–24 ×1 +227 % (Sharpe 1,49, DD 35 %) vs B&H koše +280 % (1,49, DD 40 %); závěrečný test 2025–26 ×2 −37,0 % vs B&H −41,5 %, ale prosté 50/50 bez žebříku jen −20,7 % ⇒ dokupování v medvědím trhu škodí (PF tranší 0,34). DSR 0,28. Přepočet z trades.csv: 18 bloků, 0 neshod.
- Pozn.: 1 test TV selhal — chyba testu (závisí na čase 00–02 UTC), ne produkce; návrh opravy v STATE.md, čeká na vás.
- DB 21,2 %. Od vás: R8/R9 dál čekají na uvolnění (jinak příště R10 / 3 nové hypotézy); PR #8/#9/#10 na review.

## 2026-11-07 01:10 SEČ (běh #27)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, testy OK, 0 chyb, 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Výzkum R5 **Blízkost ročnímu maximu (měsíčně držet 3 z 8 aktiv nejblíž 52týdennímu maximu)** — **ZAMÍTNUTO** ([PR #28](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/28)): validace 2023–24 ×1 +276 % (Sharpe 1,44, DD 32 %) vs B&H koše +280 % (1,49, DD 40 %); závěrečný test 2025–26 ×2 −26,9 % vs B&H −41,5 %; DSR 0,26.
- Klíčové: 3 aktiva *nejdál* od maxima (placebo) vydělala skoro stejně (+270 %) ⇒ pořadí nenese informaci. Čísla nezávisle přepočtena z trades.csv (17 bloků, 0 neshod).
- DB 21,1 %. Další běh: R7 kontrariánský žebřík (PR #31). Od vás: R8/R9 dál čekají na uvolnění; PR #8/#9/#10 na review.

## 2026-11-06 20:20 SEČ (běh #26)
- Nasazeno: `fd6065b` – PR #5 ano. Produkce beze změny: 6× HTTP 200, testy OK, 0 chyb (log API už funguje), 0 událostí, 0 nových duplicit, P/L součet −3 144,10.
- Výzkum R7 **Kontrariánský žebřík (dokupování při propadu 20/30/40 % pod ročním maximem), 8 aktiv** — připraveno ([PR #31](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/31)): protokol commitnut předem, kód + 13 testů OK. Zatím žádná čísla — denní limit 3 nových hypotéz je dnes vyčerpán; zítra poběží R5 a R7.
- Rozšířil jsem ho z BTC na koš 8 aktiv (před daty): samotné BTC má málo propadových cyklů a nesplnilo by počet obchodů z konstrukce.
- DB 21,0 %. Od vás: R8/R9 dál čekají na uvolnění; PR #8/#9/#10 na review. Běh #25 (18:04 SEČ) skončil bez reportu, nic se nepoškodilo.


## 2026-11-06 18:35 SEČ (ruční běh — audit dat, sémantika fundingu)
- Audit dat obou PR proběhl (žádná výkonnost). Interval fundingu se v 2020–2026 měnil jen u SOL v 11/2022; rozhodnuto čtení „B“ (záznam popisuje úsek, který jím končí), kód upraven, 0 nesouladů na skutečných datech.
- Výpočet výkonnosti je v obou runnerech zablokovaný (`performance_hold`), uvolníte ho jen vy. Zjištěny chybějící dny v datech (28. 10. 2026; u XRP/SOL/LTC 26.–28. 2. a 1.–2. 4. 2022) — před výpočtem nutný dodatek.
- Soubor oponentury ChatGPT kola 4 zatím nedorazil.

## 2026-11-06 18:30 SEČ (ruční běh — oponentura ChatGPT, kolo 3)
- Další 4 skutečné chyby (všechny reprodukovány, opraveny před daty): PR #29 výběr koše závisel na existenci budoucí vstupní svíčky (`8a008b6`); PR #30 nejednotná hranice dne, `day_close` mohla vzít budoucí cenu, náhradní ceny fundingu bez označení a kontroly úplnosti (`0a8373b`). Testy 37 + 31, CI zelené.
- Nově zítra nejdřív jen audit dat (sémantika intervalu fundingu), výkonnost až po rozhodnutí. Soubor pro ChatGPT: `reports/chatgpt-round4-20261106.md`.

## 2026-11-06 18:05 SEČ (ruční běh — oponentura ChatGPT, kolo 2)
- ChatGPT našel 4 skutečné chyby v PR #29 (způsobilost bez kontroly mezer, benchmark perpů bez fundingu, likvidace na výstupní hraně, pád při nedefinovaném DSR); všechny reprodukovány a opraveny před daty (`b5999e6`, 33 testů). Chyby benchmarku a DSR byly i v PR #30 — opraveno spolu s body G (`e77f2f9`, 25 testů).
- Žádná reálná data ani výsledky před opravami neexistovaly ⇒ nejde o úpravu po pohledu na výsledky.
- Nový úkol R10 (rekonstrukce N); N = 159 je pracovní odhad. Odpověď a kód pro ChatGPT: `reports/chatgpt-round3-20261106.md`.

## 2026-11-06 17:25 SEČ (ruční běh — oponentura ChatGPT, kolo 1)
- ChatGPT neměl přístup (404 kvůli tečce v názvu repa; repo je veřejné) ⇒ předávací soubor `reports/chatgpt-review-packet-20261106.md`.
- Jeho 7 kontrolních otázek k PR #29 ověřeno testy: 5 nových regresních testů (hrany fundingu, změna budoucích dat, náklady 4 noh) — 21 passed (`043666f`). Oprávněná námitka: benchmark B&H má 100 % expozice vs 40 % strategie ⇒ před daty doplněno informativní B&H se stejnou volatilitou (kritéria beze změny).
- K rozhodnutí vlastníka (návrh obou asistentů): forward PAPER vyhodnocovat jednou po 365 dnech a ≥ 30 obchodech místo „po 60 dnech“; B2 počítat proti B&H se stejnou volatilitou.

## 2026-11-06 17:05 SEČ (ruční běh — spolupráce s ChatGPT)
- Založen `automation/DIALOG.md`: kolo 1 = 5 otázek Clauda pro ChatGPT (modelování maker exekuce, oponentura PR #29, beta-neutralita, nové zdroje dat, váha forward PAPER). Autopilot ho od teď čte každý běh (RUNBOOK krok 8).
- Od vás: zkopírovat kolo 1 do ChatGPT a jeho odpověď vložit do DIALOG.md nebo poslat sem.

## 2026-11-06 16:55 SEČ (ruční běh — vaše 3 hypotézy)
- **H1 Funding settlement pressure — DUPLICITNÍ, netestováno**: stejné pravidlo (po settlementu funding pod 10. percentilem posledních 90 ⇒ obchod proti) už propadlo jako `funding_reversal` (321 obchodů, PF 0,76, ×2 0,59) a `eth_funding_extreme`; nové jsou jen parametry na opotřebovaných datech.
- **H2 Průřezová disperze fundingu, 8 perpů — ve frontě (R8)** ([PR #29](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/29)): nový mechanismus, protokol zmrazen předem, kód + 9 testů OK.
- **H3 Spot-led 5m — ve frontě (R9, nízká priorita)** ([PR #30](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./pull/30)): částečný překryv s `flow_pressure` a `btc_lead_lag`; protokol předem, kód + 11 testů OK.
- Čísla zatím nejsou: denní limit 3 nových hypotéz je dnes vyčerpán ⇒ backtesty H2 a H3 poběží 7. 11. po R5. Podrobně `reports/claude-hypotheses-triage-20261106.md`. Produkce beze změny.

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
