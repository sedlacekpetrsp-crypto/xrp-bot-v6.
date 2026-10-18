# V44–V45: relativní cena XRP/BTC

Pravidla předem pevná. Logaritmus poměru XRPUSDT/BTCUSDT se normalizuje
průměrem a populační směrodatnou odchylkou předchozích168 celých hodin.
Aktuální hodina není v odhadu; předchozí a aktuální z-skóre mají stejný
průměr a odchylku. Prvních200 hodin bez signálu. Sd<1e-12 znamená bez vstupu
a signál k uzavření. Poměr není prokázaně stacionární ani kointegrovaný.

V44: předchozí z<=−2, aktuální −2<z<0; nákup při návratu z relativní slabosti.
Výstup z>=0, stop2,5×ATR14 XRP, cíl5×ATR14, nejvýše72h.
V45: předchozí z<=2, aktuální z>2; nákup relativního průrazu.
Výstup z<0,5, stop2,5×ATR14, bez cíle, nejvýše168h.
Obě: BTC close musí být nad SMA168 včetně aktuální uzavřené hodiny;
nesplnění také uzavírá pozici. ATR14 včetně aktuální uzavřené hodiny.
Vstup pouze při překřížení, nikoli opakovaně během stejného překročení.

Pouze spot LONG XRP, BTC slouží jako vstupní údaj. Žádný short BTC, žádná
párová arbitráž, zajištění ani páka. Riziko0,5 %, alokace35 %, účet10 000 USDT.
Poplatek0,10 %, skluz0,03 %, halfspread0,01 % na stranu, stres dvojnásobek.
Uzavřené hodinové signály, provedení další5m open, stop/target kontrolovány5m.

Původní4 vývojové bloky duben2023–září2026 a souvislý běh. Brány neměnné:
3/4 kladné bloky,60 obchodů, PF>=1,2, DD<=10 %, intrabar<=12 %, kladný stres
a dolní95% bootstrap mez denního P/L nad0. Nulové náklady a koncentrace
po výsledku slouží jen diagnostice. Žádná optimalizační mřížka.

S dřívějšími V19/V20 sdílí použití BTC; nová je normalizovaná hladina poměru
namísto rozdílu24h výnosů. Další název neznamená nezávislý statistický test.
Všechna vývojová data již použitá. Bootstrap není korigován na45 variant.
Rok2022 prohlédnutý po V38; rok2021 se neotevírá. Bez dalšího ověření není
žádný výsledek schválením PAPER/LIVE. Ostatní boty se nemění.
