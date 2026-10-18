# V59 — širší hranice trendového výstupu V57

Hypotéza po výsledku V57: příliš citlivý výstup kolem hodinového adaptivního
průměru může zkracovat obchody a zvyšovat význam nákladů. V59 testuje jedinou
změnu: výstup vyžaduje dvě po sobě jdoucí uzavřené hodinové close pod
A[k]−ATR14[k], respektive A[k−1]−ATR14[k−1]. Každý bar používá vlastní tehdy
známý průměr i ATR. Pevný buffer1 ATR, bez hledání nejlepší velikosti.

Původní vstupní signály, stop distance3 ATR, žádný target, max84 hodin,
velikost pozic a náklady zůstávají shodné s V57. Počáteční stop-loss se
NEPOSOUVÁ; buffer ovlivňuje pouze trendový výstup. To může také prodloužit
ztrátové obchody a změnit, které další signály jsou dostupné bez pozice.
Nejde o opravu účetní chyby ani nezávislou novou strategickou rodinu.
V57 nezměněná kontrola; její celý původní souhrn musí být reprodukován.

Účet10000 USDT, risk0,5 %, max35 % alokace, jedna spot LONG bez páky.
Fee0,1 %, slip0,03 %, half-spread0,01 % na každé straně; stress vše2×.
Duben2023–září2026, stejné4 samostatné bloky a souvislý běh. Původní brány:
>=3/4 kladné bloky,>=60 obchodů,PF>=1,2,close DD<=10 %,intrabar<=12 %,
kladný stress a dolní95%7denní bootstrap mez denního P/L>0. Navíc nejméně
jeden obchod týdně v průměru KAŽDÉHO bloku, trades×7>=počet dní. Frekvence
není požadavek vynucovat obchody ani garance každého kalendářního týdne.

Zmrazit před výsledkem. Po výsledku porovnat skutečnou frekvenci, držení,
náklady, typy výstupů a nulové náklady, bez dalšího ladění.2021 neotevřen,
2022 spotřebován V38,2023–26 opakovaně použitá vývojová data, nikoli OOS.
Žádné PAPER/LIVE ani změna ostatních běžících botů.
