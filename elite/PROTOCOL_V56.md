# V56 — návrat nad adaptivní průměr na4h

Hypotéza: citlivost trendového průměru přizpůsobená přímočarosti pohybu může
omezit falešné vstupy v chaotickém trhu. Jde o trendovou rodinu, příbuznou
předchozím strategiím, nikoli novou nezávislou informaci nebo data.

Na úplných UTC4h close adaptivní průměr: první hodnota na indexu9 je SMA10.
Od indexu10 ER=abs(close[k]−close[k−10])/sum(abs(delta close),posledních10 změn),
při nulové dráze ER=0. SC=(ER×(2/3−2/31)+2/31)^2;
A[k]=A[k−1]+SC×(close[k]−A[k−1]). Délky10/2/30 pevně před výsledkem.

Od indexu48 vstup při překřížení close z<=A na>A, současně A[k]>A[k−6],
close>SMA42 a aktuální SMA42>SMA42 před6 bary. Žádný BTC filtr. Stop3 ATR14,
bez pevného targetu, exit po dvou po sobě uzavřených4h close<A nebo14 dnech
(4032 pětiminutových barů). Vstup následující5m open. Jeden pokus na překřížení;
neopakuje se jen proto, že pozice skončila. V18 jen reprodukční kontrola.

Stejný účet10000 USDT, risk0,5 %, max35 % alokace, jedna spot LONG bez páky.
Fee0,1 %, slip0,03 %, half-spread0,01 % na každé straně; stress vše2×. Čtyři
samostatné vývojové bloky2023 od dubna/2024H1/2024H2/2025–září2026 a souvislý běh.
Brány nezměněny:>=3/4 kladné,>=60 obchodů,PF>=1,2,close DD<=10 %,intrabar<=12 %,
kladný stress a dolní95%7denní block-bootstrap mez průměrného denního P/L>0.

Žádné ladění délek a výstupů po výsledku. Při neúspěchu diagnostika nulových
nákladů, koncentrace výnosů a rekonciliace knih.2021 neotevřen,2022 spotřebován
V38,2023–26 vývojová opakovaně použitá data. Žádné PAPER/LIVE nasazení ani
zásahy do ostatních botů. Pravidla uložit před spuštěním backtestu.
