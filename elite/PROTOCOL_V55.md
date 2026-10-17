# V55 — návrat nad cenu váženou objemem od výprodeje

Hypotéza: po výprodeji s mimořádným objemem vyčkat potvrzení zotavení nad
objemově váženou cenou od jeho začátku. Příbuzná rodina obratových/VWAP
hypotéz V34/V43, ale nové ukotvení událostí a jiný stavový vstup. Nikoli
nová nezávislá data. Žádný BTC filtr; V18 jen kontrola reprodukce.

Úplné UTC4h bary. Výprodej: close<open, high−low>=2 ATR14 z PŘEDCHOZÍCH
14 barů a objem>=2×průměr PŘEDCHOZÍCH20 barů. Průměrný objem musí být>0.
Nový výprodej nahradí staré čekající nastavení, nemůže vstoupit ve vlastní
svíčce. Ukotvit součet volume a součet5m typical-price×volume od začátku
výprodejové4h svíčky. Typical price=(high+low+close)/3. Jde o OHLC aproximaci
VWAP, ne přesný tickový VWAP. Směrový taker-buy údaj se pro signál nepoužívá.

Následujících1–6 čtyřhodinových barů čekat překřížení: předchozí close<=
předchozí ukotvený VWAP a nové close>nový VWAP včetně nového baru. Stopová
úroveň=minimum výprodejové svíčky−0,5 ATR při ukotvení. Dotyk stopové úrovně
v čekací svíčce ruší nastavení před případným vstupem. Po6 barech expirace.
Jeden pokus; cíl2×(signální close−stop) musí být>=2 % close. Zamítnutí kvůli
malému cíli také spotřebuje nastavení. Vstup následující5m open, stop/cíl
jako vzdálenosti od provedené ceny; gap tedy posune absolutní stop. Výstup
stop/target nebo7 dní (2016 pětiminutových barů). Bez následného VWAP výstupu,
aby nová ukotvení neovlivňovala starou otevřenou pozici.

Stejný engine, účet10000 USDT, spot LONG bez páky, riziko0,5 %, max35 % alokace,
jedna pozice. Fee0,1 %, slip0,03 %, half-spread0,01 % na stranu; stress vše2×.
Stejné4 vývojové bloky a souvislé období duben2023–září2026. Nezměněné brány:
>=3/4 kladné bloky,>=60 obchodů,PF>=1,2,close DD<=10 %,intrabar bound<=12 %,
kladný stress P/L a dolní95%7denní block-bootstrap mez denního P/L>0.

Pravidla zmrazit před výsledky. Diagnostika nulových nákladů a koncentrace
není výběr nové varianty.2021 neotevřen,2022 spotřebován V38,2023–26 vývojová
opakovaně použitá data. Žádný PAPER/LIVE ani zásah do ostatních botů.
