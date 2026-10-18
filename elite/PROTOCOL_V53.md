# V53 — týdenní regresní trend na4h cenách

Hypotéza: růst rozložený v celém týdnu může pokračovat i bez průrazu maxima.
Samostatný cenový vstup, žádný BTC filtr ani pivotová formace. V18 kontrola.
Jde stále o trendovou rodinu, nikoli o nezávislost na předchozím výzkumu.

Na42 úplných UTC4h close odhadnout OLS přímku log ceny vůči indexu0–41.
Skóre=slope/sqrt(max(SSE/40,1e-24)/Sxx). Skóre je indikátor hladkosti trendu,
NENÍ test statistické významnosti: rezidua finančních cen nejsou nezávislá.
Kvalifikace: skóre>=3 a slope×42>=log(1,02). Druhá podmínka měří velikost
historického sklonu; není předpovědí zaručeného výnosu.

Vstup jen při přechodu nekvalifikovaný→kvalifikovaný. Při prvním dostupném
okně je předchozí stav nekvalifikovaný. Cíl6 ATR14 musí být alespoň2 % close.
Odmítnutý malý cíl spotřebuje přechod stejně jako signál během otevřené pozice.
Stop3 ATR, cíl6 ATR od vstupní ceny. Výstup při skóre<=0 nebo po7 dnech
(2016 pětiminutových barů); stop/target zůstávají aktivní uvnitř4h. Vstup
na následujícím5m open po uzavření4h. Není použit výhled do budoucna.

Pevné parametry bez hledání nejlepší kombinace. Stejný engine, účet10000 USDT,
riziko0,5 %, max35 % alokace, jedna spot LONG pozice, bez páky. Každá strana:
fee0,1 %, slip0,03 %, half-spread0,01 %. Stress vše2×. Čtyři samostatné bloky
2023 od dubna,2024H1,2024H2,2025–září2026 plus souvislý běh. Brány nezměněny:
>=3/4 kladné bloky,>=60 obchodů,PF>=1,2,close DD<=10 %,intrabar bound<=12 %,
kladný stress P/L a dolní95%7denní block-bootstrap mez denního P/L>0.

2023–26 vývojová opakovaně použitá data,2022 spotřebován V38,2021 neotevřen.
Nová varianta neobnovuje nezávislost dat. Žádná automatická PAPER/LIVE
aktivace ani změny ostatních botů. Při neúspěchu pouze diagnostika nulových
nákladů, koncentrace výnosů a účetních knih; žádné následné ladění prahů.
