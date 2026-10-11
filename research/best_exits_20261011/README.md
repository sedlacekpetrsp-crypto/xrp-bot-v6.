# BEST – technická oprava a test výstupů, 11. 10. 2026

## Rozhodnutí

Varianta bez posunu stop-lossu na break-even NEPROŠLA. Nevzniká kandidátní PAPER bot ani další placená služba. Obchodní signály, původní SL, TP a posun BE v nasazeném BEST se nemění. Technická oprava kontrol rizika a rozdělení statistik je samostatná změna.

## Technická oprava

Commit určený pro stávající Render službu: `47e2acc2785268463118f87a85e7b79645d746f5`, větev `v8-fly-layer-test`.

- BREAKOUT, FIB i EMA 4h nyní používají společnou kontrolu vstupu a povoleného rizika.
- Koordinátor nesmí zvýšit místní limit. Nulový/neplatný limit, chyba koordinátoru nebo neúplná obnovená pozice blokují nový vstup.
- Započítává se počáteční riziko a nominální velikost již otevřených pozic; původní společný limit dvou pozic zůstává.
- Obnovené EMA pozice omezují nové vstupy původní strategie stejným způsobem. Ověřeno maketou DB, nikoli testem pádu skutečného Postgresu.
- Přehled odděluje BREAKOUT, FIB a EMA 4h; staré souhrnné API skupiny zůstávají pro kompatibilitu.
- Historie a nastavení ostatních botů nejsou přepisovány. BEST je nadále pouze PAPER.

Oprava hooku znamená, že se konečně uplatní existující limit koordinátoru BEST (0,1 % referenčního zůstatku, dle stávající implementace). Jde o omezení velikosti nových pozic, nikoli novou vstupní strategii. Referenční zůstatek koordinátor odvozuje od více botů; replay souběh botů nesimuluje.

## Skutečný PAPER stav před nasazením

Snapshot endpointu `/bestof/status` dne 11. 10. 2026: Postgres, žádná otevřená pozice, balance 9 929,671906638316 USDT, 47 uzavřených obchodů. Souhrnný P/L −70,32809336168235 USDT.

| Strategie | Obchody | Čistý P/L USDT | PF |
|---|---:|---:|---:|
| BREAKOUT | 34 | −63,20 | 0,760 |
| FIB | 13 | −7,13 | 0,933 |
| EMA 4h | 0 | 0,00 | nelze hodnotit |

Jde o dostupnou historii, ne o důkaz budoucího výkonu. Nula u EMA neznamená ziskovou ani ztrátovou strategii.

## Předem stanovený test break-even

Protokol byl commitnut před výpočtem. Jediná hypotéza: BE při +0,75R může ukončovat budoucí ziskové obchody. Obě ramena používají stejná data, signály, počáteční SL, TP, riziko i nové místní portfolio kontroly. Jedinou experimentální změnou je vypnutí BE v offline přehrávači.

Data všech čtyř trhů prošla přesnou kontrolou SHA256 proti původnímu manifestu. 5minutové OHLC neumí reprodukovat 3sekundovou cestu ceny. EMA 4h a souběh s jinými boty jsou mimo replay. Financování shortů chybí stejně jako v původním modelu. P/L zahrnuje modelované poplatky a skluz.

| Varianta | Vývoj P/L | Ověření P/L | Obchody ověření | PF | Max. pokles | P/L při 2× skluzu |
|---|---:|---:|---:|---:|---:|---:|
| Současný BE, opravené místní limity | −555,25 | −450,72 | 152 | 0,671 | 4,622 % | −562,64 |
| Bez posunu BE | −496,90 | −437,97 | 148 | 0,690 | 4,868 % | −592,58 |

Vývoj: 4. 7.–31. 8. 2026. Chronologické ověření: 1. 9.–1. 10. 2026. Každé okno začíná na 10 000 USDT; nesčítat jako souvislý výsledek. Dříve použitá data nejsou neviděný holdout. Drobné odchylky základu od předchozího README vznikají uplatněním opraveného společného místního rozpočtu rizika; původní výsledky zůstaly zachovány.

Varianta splnila pouze počet obchodů. Nesplnila kladný čistý výsledek, PF ≥1,1, pokles nehorší než základ ani kladný výsledek při dvojnásobném skluzu. Nevhodná k propagaci. Rozpad replay výsledků po strategiích a úplné seznamy obchodů jsou v `results/`.

## Budoucí ověření a omezení

V protokolu je předem vyhrazené budoucí okno 12. 10.–11. 11. 2026 UTC. Dnes nemůže mít výsledky. Protože kandidát neprošel ani diagnostickou branou, automatický kandidátní PAPER provoz není spuštěn a není naplánované samovolné nasazení. Další výzkum musí zachovat zmrazený protokol; žádné dodatečné vybírání parametrů podle tohoto výsledku. Budoucí data se opatří otisky po jejich získání.

Původní záznam dalších technických rizik zůstává v `../best_validation/known_issues.md`: zejména atomické vypořádání obchodu a chování skutečné DB při pádu mezi zápisy tato oprava neřeší. Úspěšný restart bez otevřené pozice není důkaz odolnosti proti všem pádům.

## Reprodukce

```bash
python research/best_validation/download_data.py --output /tmp/best-data
python -m unittest research.best_validation.test_replay test_bestof_ema4h test_bestof_ema4h_persistence test_bestof_portfolio research.best_exits_20261011.test_exits -q
python -m research.best_exits_20261011.run --data /tmp/best-data
```

26 cílených testů: původní dvě očekávaná selhání nyní skutečně procházejí; nový test prokazuje změnu BE bez odstranění původního stop-lossu. Nasazovaná větev samostatně prošla 16 testy a importem společné aplikace.
