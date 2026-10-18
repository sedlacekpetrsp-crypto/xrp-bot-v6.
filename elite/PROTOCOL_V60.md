# V60 — vyšší frekvence na výslovnou žádost18.10.2026

Kontrolovaná odvozenina hodinové V57: odstranit její42barový pomalý trendový
vstupní filtr (close>SMA42 a SMA42 roste proti6 barům zpět). Zachovat
překřížení close nad adaptivní průměr10/2/30 a jeho růst proti6 barům zpět.
Zůstává stejný warmup48 barů. Všechny původní vstupní signály musí zůstat
v signálovém toku; skutečně uskutečněné obchody se mohou změnit obsazením
jediné pozice novými signály. V57 původní kontrola, nikoli V59.

Stop3 ATR, bez targetu, trendový exit dvěma close pod adaptivním průměrem
BEZ bufferu, max84h. Vstupy následující5m open po úplné UTC hodině. Stejné
pozice, risk0,5 %, max35 % alokace, účet10000 USDT, spot LONG bez páky.
Fee0,1 %,slip0,03 %,half-spread0,01 % na stranu;stress vše2×.

Nový výzkumný cíl aktivity před výsledkem: alespoň3 obchody týdně v průměru
KAŽDÉHO ze4 bloků (trades×7>=3×počet dní). Přesnou cílovou frekvenci uživatel
nezadal, jde o pracovní cíl na jeho požadavek dalšího zvýšení. Není příkaz
vynucovat obchod ani záruka každého týdne. V57 kontrola si zachovává původní
bránu1 týdně. Původní finanční brány neměnit:>=3/4 kladné,>=60 obchodů,
PF>=1,2,close DD<=10 %,intrabar<=12 %,kladný stress a dolní95%7denní block
bootstrap mez denního P/L>0. Data duben2023–září2026,stejné4 bloky+souvislý běh.

Hypotéza: pomalý filtr omezuje příležitosti; jeho odstranění má zvýšit aktivitu.
Riziko: přidá špatné vstupy v poklesu. Výhodu nelze předpokládat z vyššího počtu.
Zmrazit před testem, žádná další optimalizace prahů po výsledku. Diagnostika
nulových nákladů, frekvence/mezer, držení a koncentrace výnosu.

2023–26 opakovaně prohlédnutá vývojová data,nikoli OOS;2022 spotřebován V38,
2021 neotevřen. Žádné PAPER/LIVE nasazení ani změny ostatních běžících botů.
