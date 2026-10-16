# Audit simulátoru16.10.2026

Nejde o novou strategii ani hledání ziskového nastavení. Nejdříve ruční
účetní příklady, potom testy vadných vstupů, oprava a přesné srovnání evidence.
Základní účetní fixtures prošly již před opravou.12 vadných subpřípadů
nebylo odmítnuto:3 tržní řady a9 neplatných instrukcí. Výsledek zachován.

Oprava: simulate() sám validuje celou řadu OHLC a5m kadenci; spotřebované
signály musí mít konečné nezáporné vzdálenosti stop/target/trailing,
celočíselný nezáporný max_bars a bool exit. Nic se automaticky neopravuje.
Přijímací brány, fill logika, náklady a velikosti pozic nezměněny.

Přímý replay V18,V38,V49 za celé vývojové období duben2023–září2026 při
základních a dvojitých nákladech. Porovnat přesně všechny obchody,denní
equity,souhrnné metriky a události pauz s již uloženou plnou evidencí.
V38 používá stejnou V18 a prázdnou nepoužívanou strict větev (jen V39 ji čte).
Real-data prefix test V18 a V49 na půlce historie+5 svíček, včetně neúplné
hodiny. Stavové chování V38 pokrývají stávající unit testy a úplný replay.

Audit je omezený: žádný důkaz absence všech chyb, model5m nemá pořadí ticků,
stop před target při souběhu a konzervativní gap target zůstávají předpoklady.
Intrabar DD je konzervativní mez, ne skutečný tickový průběh. Data od datového
loaderu byla již dříve validována; chyba hranice API sama nedokazuje, že staré
backtesty použily vadná data. Neotevírat2021 ani2022,žádné nasazení.

Historické protokoly/hash guards se nemění. Starý challenge V38 může být
znovu reprodukován na původním zmrazeném commitu; po změně engine hash guard
správně odmítne považovat nový kód za původní. Tento audit není novým OOS.

Cross-runtime kontrola nalezla pouze rozdíl PF V49 stress:
Python3.11 0.6442399315550612 vs reference3.12 0.6442399315550604.
Stejné ledgery,denní equity a ostatní metriky. Sekvenční součet původního
ledgeru přesně reprodukuje hodnotu3.11. Pro bitově přesný audit sjednoceno
CI na Python3.12, shodně s lokálním zdrojem reference. Žádná tolerance
ani změna přijímacích bran; audit nadále vyžaduje přesnou shodu všech polí.
