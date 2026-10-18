# V51: jediný vstupní pokus v epizodě průrazu,16.10.2026

Jeden navazující experiment, žádná mřížka parametrů. V18 tvoří nezměněnou
kontrolu. Hypotéza: opakované průrazové signály ve stejné epizodě mohou
vytvářet dodatečný obrat a ztráty po stopu. Nejde o předpoklad, že to tak
skutečně je; počet změněných obchodů a výsledky hypotézu musí ověřit.

Epizoda: souvislá řada uzavřených hodin, kdy původní XRP V5 má kladnou
stop_distance, tedy close nad maximem předchozích72 hodin. V51 umožní
vstup jen první hodinu epizody, a pouze pokud zároveň povoluje původní V18
(BTC filtr). Pokud BTC dovolí vstup až později ve stejné epizodě, nevstupovat.
Nová epizoda může začít až po alespoň jedné hodině bez průrazu XRP.
Nezávisí na výsledku ani stavu pozice; pokus může být spotřebován během držení.

Původní stop3ATR14, výstup pod24h minimum, bez cíle/časového limitu,
riziko0,5 %,alokace35 %,spot LONG bez páky,10 000 USDT; bez dalších změn.
Fee0,10 %,skluz0,03 %,halfspread0,01 % na stranu; stres dvojnásobek.
Uzavřené hodinové signály, další5m open, stop kontrolován5m.
Po200 hodinách rozehřátí; předchozí dostupný raw signál inicializován false.
Indikátorové epizody používají minulou historii před resetem účtu v bloku.

Stejná4 resetovaná období duben2023–září2026 a souvislý běh. Brány neměnné:
3/4 kladné bloky,60 obchodů,PF>=1,2,DD<=10 %,intrabar<=12 %,kladný stres,
dolní95% bootstrap mez denního P/L nad0. V18 kontrola musí reprodukovat
původní výsledky. Počítat vstupní signály a skutečné obchody odděleně.

Vývojová data již použitá, intervaly bez korekce na51 verzí. V51 je odvozenina
V18, ne nezávislá rodina. Rok2022 již prohlédnut, rok2021 tento běh neotevírá.
Případný vývojový průchod vyžaduje předem zmrazené další ověření a prospektivní
data; žádné automatické PAPER/LIVE schválení. Ostatní boty beze změny.
