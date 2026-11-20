# K11 BINANCE_SPOT_DELIST_DRIFT — protokol KROKU 0 (jen datový audit, žádný výnos)

Stav: **NÁVRH k oponentuře ChatGPT** (autopilot běh #83, 2026-11-19). Zapsán **před stažením jakýchkoli dat**.
Režim: výhradně PAPER / výzkum. Žádný výkonnostní výpočet, žádné ladění. Výkon (krok 1) jen samostatnou
předregistrací po GO kroku 0, po oponentuře a se souhlasem vlastníka.

## 1. Hypotéza a ekonomický mechanismus
Po oznámení Binance „Binance Will Delist <TOKEN>“ (spotové vyřazení) cena tokenu v následujících dnech až do data
vyřazení dál klesá (post-announcement drift), protože:
1. **Nucená/organizovaná migrace držitelů:** Binance je pro většinu malých altcoinů dominantní spotové místo; držitelé
   musejí do termínu prodat nebo přesunout tokeny na méně likvidní burzu ⇒ jednostranný prodejní tok rozložený do dnů.
2. **Odchod tvůrců trhu a pokles hloubky:** po oznámení se spready rozšiřují a nákupní strana řídne (stejný prodejní
   tok má větší cenový dopad).
3. **Omezení arbitráže:** short je možný jen přes perp (pokud existuje); ten Binance často delistuje dřív nebo současně ⇒
   arbitráž driftu je kapitálově i operačně omezená.
Prediktivní tvrzení: kumulovaný výnos perpu tokenu od `t_ann + L` do `min(t_ann + H, perp_last_trade − 1 h)` je
v průměru záporný i po očištění o trh, a to o víc než 3× all-in náklad.

## 2. Novelty gate (RESEARCH_FRAMEWORK §6)
| Řádek | Odpověď |
|---|---|
| Testovaná rodina | Registr + inventář 110 + K1–K10 prohledány (grep `delist|announce|monitoring`): delisting se objevuje jen jako **nucený výstup** v A1/A2 (PR #38/#39/#41). Nejbližší rodiny: A1 NEW-LISTING DRIFT (zamítnuto), A5 SPOT-LISTING DRIFT (DATA NO-GO, 55 událostí), A6 zprávy (DATA NO-GO, chyběl PIT archiv). |
| Rozdíl mechanismu | ANO: spouštěč je **oznámení burzy o odstranění trhu** (diskrétní šok likvidity a nucený prodejní tok), ne stáří kontraktu (A1), ne nový spotový trh (A5), ne sentiment titulků (A6). Žádná varianta A1 (short „starých“ listingů). |
| Měřitelnost mechanismu | ČÁSTEČNÁ: spouštěč (čas oznámení) i zprostředkující proměnné **lze měřit z Binance Vision**: spotový `quote_volume` a taker sell podíl po oznámení vs. před (tok prodejů), denní rozpětí high/low jako proxy hloubky. Hloubku knihy historicky nemáme ⇒ mechanismus 2 jen přes proxy (uvést jako omezení). |
| PIT zdroj / dostupnost | Čas oznámení: Binance CMS (veřejné `bapi/composite/v1/public/cms/article/list/query`, katalog Delisting) — `releaseDate` (ms). PIT ověření: Wayback snímky stránky kategorie (snímek ≤ `releaseDate` + 24 h musí obsahovat titulek). Ceny: Binance Vision spot + UM 1m/1h klines vč. delistovaných symbolů (SHA-256 z `.CHECKSUM`), funding `fundingRate`. Vše zdarma, stahuje jen GitHub Actions. |
| Instrument, likvidita | Short USDT-M perpu tokenu na Binance, **jen pokud perp existuje a je obchodovatelný** v `t_ann + L` (z `listings.csv` PR #38 / UM klines). Bez perpu událost nevstupuje (spot short neexistuje). |
| All-in náklady | Taker 0,05 % + skluz 0,02 %/stranu (×1/×2/×3; pro malé altcoiny po oznámení navíc stres skluz ×3 povinně), funding (u crowded shortu může být silně záporný ⇒ náklad shortu), nucený výstup při delistingu perpu. |
| Filtr hrana ≥ 3× náklad | **Opora jen anekdotická** (jednotlivé případy, např. CryptoQuant quicktake k ALCX 2026; žádná ověřená studie post-announcement driftu na Binance perpech). Proto krok 0 NEPOČÍTÁ výnos a 3× filtr se ověří až předregistrovaným krokem 1 na vývojovém úseku (předbrána hrubě ≥ 3 × all-in RT). |
| Chronologické OOS | Odhad z veřejných seznamů: desítky až nízké stovky spotových delistingů 2020–2026; kolik z nich mělo obchodovatelný perp v `t_ann + L`, je hlavní otázka kroku 0 (brána níže). |
| Verdikt | GO **jen pro krok 0** (datový audit). |

## 3. Krok 0 — co se měří (bez výnosů)
Jediný výstup = tabulka událostí `events.csv` a `step0_manifest.json`; **žádné ceny po `t_ann`** se nečtou kromě
kontroly existence svíček (počet řádků) a časových razítek.
1. **Výčet oznámení:** všechny články katalogu Delisting 2020-01-01..2026-10-31; parsovat `title`, `releaseDate`,
   seznam tokenů a datum/čas spotového delistingu z titulku/těla. Články „Monitoring Tag“, „Vote to Delist“,
   margin/earn/futures-only delistingy se vedou zvlášť (typ události), do hlavní populace jen **spotový delisting**.
2. **PIT ověření času:** pro každé oznámení nejbližší Wayback snímek stránky kategorie po `releaseDate`;
   `pit_ok` = titulek nalezen ve snímku ≤ `releaseDate` + 24 h a nalezen v žádném snímku před `releaseDate` − 24 h.
   Bez snímku ⇒ `pit_unverified` (do populace NEVSTUPUJE; žádná imputace).
3. **Obchodovatelnost perpu:** symbol `<TOKEN>USDT` (příp. `1000<TOKEN>USDT`) v UM klines; `perp_ok` = existuje
   souvislá 1h svíčka v `t_ann + L` (L = 60 min) a perp se obchoduje ještě ≥ 24 h po `t_ann + L`.
4. **Pokrytí dat:** 1m UM klines v okně `[t_ann − 7 d, t_ann + 14 d]` ≥ 95 % minut (do `perp_last_trade`),
   CHECKSUM 0 chyb; funding soubory pro stejné okno.
5. **Shluky:** oznámení obvykle obsahují víc tokenů najednou ⇒ evidovat `cluster_id` (stejný článek); pro power se
   počítá **počet nezávislých článků** i počet tokenů.

## 4. Brána GO (jen pro návrh výkonnostního protokolu, zmrazeno předem)
GO, pokud současně:
- (a) **≥ 60 způsobilých událostí** (`spot_delist ∧ pit_ok ∧ perp_ok ∧ coverage_ok`) a **≥ 25 nezávislých článků**;
- (b) z toho **≥ 20 událostí v závěrečném úseku** (oznámení ≥ 2025-01-01) pro chronologické OOS;
- (c) podíl `pit_unverified` mezi spotovými delistingy ≤ 30 % (jinak selekční bias PIT ověření).
Jinak **DATA NO-GO**, K11 se uzavře bez výkonu; žádné rozšíření na Monitoring Tag/margin delistingy jako náhradní
endpoint bez nové předregistrace (poučení A5/K8).

## 5. Předběžný rámec kroku 1 (jen informativně, NEZMRAZENO, schvaluje se zvlášť)
Jediný primární endpoint: abnormální výnos shortu perpu od `t_ann + 60 min` do `min(t_ann + 72 h, perp_last_trade − 1 h)`
po odečtení stejně velkého shortu PIT equal-weight koše likvidních perpů (beta 1), po nákladech ×1/×2/×3 a fundingu.
Placebo: tytéž tokeny v náhodných časech mimo ±30 d od oznámení. Inference bootstrapem přes články (shluky).
N pro DSR podle ledgeru R10b (PR #66) + 1. Vývoj = oznámení < 2025-01-01, závěr ≥ 2025-01-01 (smí jen zamítnout,
povýšení jen forward PAPER).

## 6. Rizika a omezení (předem)
- Většina reakce může proběhnout v prvních minutách po oznámení ⇒ při L = 60 min nemusí zbýt drift (to je legitimní
  negativní výsledek, ne důvod L ladit).
- Crowded short ⇒ extrémní záporný funding a short squeeze; likvidační pravidlo short nohy převzít z A1.
- Binance bapi může z IP GitHub Actions vracet 403/451 ⇒ pak zdroj = Wayback snímky seznamu článků; když ani to
  nedá úplný výčet, DATA NO-GO.
- Žádná produkční změna, žádný LIVE, žádné placené API.

## Dodatek 1 (2026-11-19, před daty; review dialog 0404) — implementace brány §4
- Brána = `research/k11_step0_gate.py::audit_gate` (ChatGPT `4402aba`/`19c71e1`, review Claude `7119e5c`), 21 syntetických testů.
- `pit_status` ∈ {ok, unverified, contradicted}: *unverified* = žádný použitelný snímek; *contradicted* = titulek nalezen
  ve snímku < `releaseDate` − 24 h (čas oznámení vyvrácen). **Obojí** se počítá do čitatele poměru §4 (c)
  (konzervativní; jmenovatel = všechny spotové delistingy), v manifestu se obojí vykazuje zvlášť.
- Oznámení mimo okno 2020-01-01..2026-10-31 UTC ⇒ chyba (fail closed), nikoli tiché vyřazení.
- Identita `article_id` (Binance CMS `code`) a `token` (spotový base asset, velká písmena) musí být už kanonická;
  aliasy perpu (`1000<TOKEN>USDT` apod.) patří do samostatného pole `perp_symbol` mapovaného výčtem, ne do `token`.
- Ostatní body protokolu beze změny; výnos se nepočítá.

## Dodatek 2 (2026-11-19, před daty; review dialog 0405) — sémantika Wayback důkazu §3.2
- Klasifikace `pit_status` = `research/k11_archive_pit_evidence.py::classify_archive_evidence` (ChatGPT `b41b7db`/`f09ad25`).
  CMS `releaseDate` sám o sobě PIT nedokládá (souhlas s ChatGPT); `ok` jen s pozitivním snímkem v [release, release + 24 h].
- **Pozorování = skutečný čas snímku z CDX API** (`timestamp` 14 číslic UTC), nikdy požadovaný čas URL `web/<ts>/…`
  (Wayback přesměruje na nejbližší snímek). Jen snímky se `statuscode` 200; 3xx/4xx/5xx se do pozorování nezapisují.
- **`present` = odkaz na článek s jeho CMS `code` (identifikátor v URL článku) ve snímku**, ne shoda textu titulku:
  Binance titulky se opakují (např. obecné „Notice of Removal of Spot Trading Pairs“) ⇒ shoda titulku by vyráběla falešná
  `contradicted`. Snímek, ve kterém seznam článků vůbec není vykreslen (SPA bez dat), se zapisuje jako *neplatný* a do
  pozorování nevstupuje (není ani pozitivní, ani negativní).
- Zdroje snímků (předem): stránka katalogu Delisting a archivované odpovědi `bapi/composite/v1/public/cms/article/list/query`
  z Wayback (pokud existují). Žádná další náhradní zdrojová cesta po zhlédnutí dat.
- Riziko předem: pokud archivované HTML neobsahuje vykreslený seznam, většina událostí bude `unverified` ⇒ brána §4 (c)
  vrátí DATA NO-GO. To je legitimní výsledek, ne důvod měnit pravidla.

## Dodatek 3 (2026-11-19, před daty; kolektor Claude, k review ChatGPT dialog 0408) — implementační volby kolektoru
Kolektor `research/k11_step0_collector.py` (testy `tests/test_k11_step0_collector.py`), workflow `.github/workflows/k11-step0.yml`
(spouští jen soubor `RUN_REQUEST_STEP0`, který se **nevytvoří před review**). Volby zmrazené před daty:
1. **Výčet:** CMS katalog 161 (Delisting), okno §3.1. Typ události z titulku pevnými pravidly (`classify_title`): monitoring_tag,
   vote_to_delist, margin_delist, futures_delist (futures/perpetual/contract), pair_removal (Removal of Spot Trading Pairs),
   spot_delist (= „Binance Will Delist <tokeny>“), jinak other. Tokeny jen z titulku (`parse_tokens`); nejednoznačný titulek ⇒
   `spot_delist_unparsed` (do populace nevstupuje, vykazuje se). **Úplnost:** podíl nečitelných spotových článků > 5 % ⇒ DATA NO-GO
   (žádné ruční doplňování po zhlédnutí). CMS nedostupné (403/451/…) ⇒ DATA NO-GO s důvodem v manifestu (záložní výčet z archivu
   by byl nová předregistrace).
2. **PIT:** CDX pro 3 pevné URL prefixy (stránka c-161, /delisting, archivované odpovědi list API), jen status 200, čas = CDX timestamp.
   Stahují se snímky v sjednocení oken `[release − 7 d, release + 24 h]` přes všechny spotové články, deduplikace přes CDX `digest`.
   Rozpor (`contradicted`) se tedy hledá jen v `[release − 7 d, release − 24 h)` — omezení kapacity Wayback; uvádí se jako omezení.
   Snímek bez jediného CMS kódu = nevykreslený, nevstupuje.
3. **Perp:** aliasy v pevném pořadí `<T>USDT`, `1000<T>USDT`, `1000000<T>USDT`, `1M<T>USDT`; vítězí první s denním 1m souborem
   v den `t_ann`. `perp_ok` = všech 60 minut hodiny obsahující `t_ann + 60 min` a poslední minuta v okně ≥ `t_ann + 60 min + 24 h`.
4. **Pokrytí:** denní UM 1m soubory `[t_ann − 7 d, t_ann + 14 d]`, každý ověřen `.CHECKSUM` (SHA-256); čte se jen `open_time`.
   `coverage_ok` = pokrytí minut ≥ 95 % (do poslední obchodované minuty) ∧ 0 chyb CHECKSUM ∧ měsíční `fundingRate` soubory
   (s CHECKSUM) pro všechny měsíce okna.
5. **Diagnostika (0407), nefiltruje:** `book_ticker_available`, `book_depth_available` = existuje Vision denní soubor v den `t_ann`.
6. Manifest zapisuje URL, HTTP status a SHA-256 každé odpovědi a SHA-256 `events.csv`. `returns_computed = false`.
7. **Upřesnění po review ChatGPT (PR #71, před daty):** `perp_ok` = 60 souvislých minut **od minuty vstupu** `t_ann + 60 min`
   (ne od začátku UTC hodiny; ChatGPT `396910b`/`e3c0de5`). Deduplikace snímků přes `digest` jen pro stažení — **všechny** časy
   snímků se stejným obsahem vstupují do pozorování. Nečíselný `open_time` mimo hlavičku ⇒ soubor neplatný (fail closed).
8. **Jmenovatel pokrytí (review ChatGPT `aa88f6a`, před daty):** §3.4 „do `perp_last_trade`“ platí jen s doloženým koncem
   obchodování = poslední minuta uprostřed UTC dne (≠ 23:59) a před koncem okna. Jinak jmenovatel = celé okno [−7 d, +14 d]
   (fail closed). Manifest navíc vykazuje citlivost `gate_sensitivity_full_window` (vždy celé okno) a počet zkrácených událostí;
   verdikt určuje primární pravidlo, rozdíl verdiktů se v RESULTS výslovně uvede. Úplné nahrazení jmenovatelem celého okna
   (návrh ChatGPT) NEPŘIJATO: vyřadilo by každou událost, kde Binance delistuje perp do 14 dnů — to je běžný průběh
   a byl by to selekční bias proti zmrazenému §3.4.
9. **Integrita `open_time` (review ChatGPT `83306d1`/`56b2985`, před daty):** jen epoch v ms (10^12–10^13) nebo µs (10^15–10^16),
   přesně na hranici minuty, jedna jednotka na soubor; jinak soubor neplatný. Přesný duplikát řádku se toleruje (množinu minut
   nenafukuje; vyřazení by jen ubíralo platná data).
10. **Revize bodu 8 (review ChatGPT `ee681b6`/`28568ee`, před daty; konzervativnější varianta):** konec 1m dat uprostřed dne
    `perp_last_trade` NEDOKLÁDÁ (stejný obraz dá výpadek archivu). **Primární `coverage_ok` = celé okno [−7 d, +14 d]**
    (odchylka od textu §3.4 „do `perp_last_trade`“ směrem k přísnosti). Zkrácené pokrytí jen jako citlivost
    `gate_sensitivity_truncated_intraday_end`. Důsledek předem: události s delistingem perpu do +14 d z populace vypadnou;
    vrátit je smí jen nový dodatek před daty s PIT zdrojem ukončení obchodování (oficiální futures oznámení s časem,
    SHA-256), např. přes modul ChatGPT `research/k11_end_evidence.py` (zatím NEINTEGROVÁN — chybí zdroj, který by ho plnil).
11. **Integrita výčtu CMS (review ChatGPT `93d3ede`/`dc6b352`, před daty):** `enumerate_cms` ověří stránky přes
    `research/k11_cms_pagination_audit.py`: chybějící/opakovaná koncová stránka, celá opakovaná stránka, duplicita v rámci
    stránky, konfliktní metadata stejného `code`, `releaseDate` jiné než kladné int ms ⇒ DATA NO-GO s důvodem. Identický článek
    na další stránce (posun stránkování při zveřejnění nového článku během výčtu) se počítá **jednou** a vykazuje
    (`identical_cross_page_duplicates`).
12. **Transportní vrstva (review ChatGPT `04affcf`/`d67183c`, před daty):** nevalidní CMS JSON/schéma ⇒ DATA NO-GO s důvodem;
    CDX prefix s HTTP ≠ 200 nebo nevalidním JSON ⇒ DATA NO-GO (ztráta prefixu by mohla skrýt rozporný snímek); CDX 200 s prázdným
    tělem = 0 snímků (legitimní). Neúspěšná stažení jednotlivých snímků (po 3 pokusech) se vykazují v
    `archive_snapshot_fetch_failures` a v RESULTS se uvede, zda mohla změnit `pit_status` (ok ↔ contradicted).
