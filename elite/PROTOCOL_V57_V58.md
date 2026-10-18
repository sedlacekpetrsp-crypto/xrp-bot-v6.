# V57/V58 — častější obchody na žádost uživatele17.10.2026

Před výsledky pevně dvě odvozeniny V56, nikoli nezávislé nové hypotézy:
V57=1h svíčky, V58=15m svíčky. Stejný adaptivní průměr10/2/30,42barový trend,
6barové porovnání, ATR14, stop3 ATR a exit dvěma close pod průměrem. V56
nezměněná4h kontrola. Výrazy weekly v původním kódu na nižších rámcích
znamenají42 barů, nikoli kalendářní týden. Veškeré cenové indikátory se tedy
zkracují v reálném čase spolu se svíčkou. Maximum držení84 strategických
barů: V57 84 hodin (1008×5m), V58 21 hodin (252×5m). Bez pevného cíle.
Signály pouze z úplných UTC svíček, provedení následující5m open.

Hypotéza: kratší horizont může zvýšit počet příležitostí. Ekonomická výhoda
se tím nepředpokládá; rizikem jsou vyšší náklady a šum. Žádné další ladění.

Nové minimum aktivity: v KAŽDÉM ze čtyř samostatných bloků nejméně jeden
realizovaný dokončený obchod za7 kalendářních dní v průměru, tj. trades×7>=
počet dní bloku. Není to požadavek na konkrétní kalendářní týden ani příkaz
obchodovat bez signálu. Jde o první výzkumné minimum zvýšené aktivity, ne o
uživatelem zadanou přesnou cílovou frekvenci. Vedle toho uvést skutečné
obchody za týden, aktivní měsíce a nejdelší mezeru mezi vstupy.

Původní finanční brány zachovány:>=3/4 kladné bloky,>=60 obchodů,PF>=1,2,
close DD<=10 %,intrabar<=12 %,kladný stress P/L a dolní95%7denní bootstrap
mez denního P/L>0. Kontrolní V56 hodnotit původními branami, nikoli zpětně
přepisovat její protokol. Účet10000 USDT,0,5 % riziko,max35 % alokace,jedna
spot LONG bez páky. Fee0,1 %, slip0,03 %, half-spread0,01 % na stranu;stress2×.

Období duben2023–září2026 vývojové a opakovaně použité.2022 spotřebován V38,
2021 neotevřen. Bootstrap neopravuje mnohonásobné hledání. Žádná automatická
PAPER/LIVE aktivace ani změna ostatních běžících botů. Uchovat obě varianty
včetně neúspěšných. Při neúspěchu pouze diagnostika, bez posouvání prahů.
