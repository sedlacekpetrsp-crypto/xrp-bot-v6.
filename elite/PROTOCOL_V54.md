# V54 — denní převaha agresivních nákupů, hodinové vyhodnocení

Hypotéza: vznik převahy taker nákupů při dosud malém růstu ceny může
předcházet dalšímu růstu. Samostatný objemový vstup, žádný průraz maxima,
BTC filtr ani regresní trend. Navazuje na objemová data V28, nikoli na její
vstupní pravidlo; není nezávislou datovou sadou.

Použít stejné checksummed XRP archivy a jejich base volume/taker-buy volume,
přesně sladěné s cenami. Agregovat úplné UTC hodiny. Za posledních24 hodin
I=(2×součet taker-buy volume−součet total volume)/součet total volume.
Jde o stranu agresora obchodu, nikoli celkový přítok peněz; každý obchod má
kupujícího i prodávajícího. Při nulovém objemu není I definováno, žádný vstup.

Vstup pouze překřížením I z<=0,05 na>0,05 (taker-buy podíl>52,5 %), současně
24h cenová změna0 až2 % včetně. Musí existovat předchozí platné I. Cíl4 ATR14
hodin musí být alespoň2 % close. Zamítnutý přechod se nepřenáší dál.
Stop2 ATR, target4 ATR od vstupní ceny. Výstup I<0 nebo48h (576 pětiminutových
barů). Signál jen uzavřená hodina, vstup následující5m open. Jedna pozice,
bez dalšího vstupu během trvající převahy. Žádné ladění prahů podle výsledků.

Účet10000 USDT, spot LONG bez páky, riziko0,5 %, max35 % alokace, stejný
engine. Fee0,1 %, skluz0,03 %, half-spread0,01 % na stranu; stress vše2×.
Čtyři vývojové bloky2023 od dubna/2024H1/2024H2/2025–září2026 a souvislý běh.
Brány:>=3/4 kladné bloky,>=60 obchodů,PF>=1,2,close DD<=10 %,intrabar<=12 %,
kladný stress a kladná dolní95%7denní block-bootstrap mez denního P/L.
Kontrola V18 musí reprodukovat původní souhrn. Diagnostika nulových nákladů,
koncentrace výnosu a účetní rekonciliace až po výsledku, ne pro výběr prahu.

Rok2021 neotevřený,2022 již spotřebován V38. Data2023–26 opakovaně použitá,
nikoli OOS. Žádný automatický PAPER/LIVE ani změny ostatních botů.
