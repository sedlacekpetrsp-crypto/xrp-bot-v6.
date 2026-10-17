# Audit nákladové citlivosti,16.10.2026

Diagnostika zmrazených V18 a V49, nikoli nové strategie či výběr parametrů.
V18 reprezentuje silnější dřívější vývojovou bilanci s nedostatečnou robustností;
V49 případ kladného beznákladového výsledku a záporného výsledku s náklady.
Volba kandidátů je založena na prohlédnutých výsledcích a není nezávislá.

Předem pevné násobky původních nákladů:0;0,25;0,5;0,75;1;2.
Každý násobek společně škáluje fee0,10 %,slip0,03 %,halfspread0,01 % na stranu.
Žádné tvrzení o dosažitelnosti na konkrétním účtu/burze. Nulové náklady jsou
pouze diagnostika. Hrubý součet sazeb není přesný výpočet realizovaných nákladů.
Původní riziko0,5 %,alokace35 %,10 000 USDT,spot LONG a signály beze změny.
Změna nákladů může měnit velikost pozice,fill i stop/target cestu a počet obchodů.

Stejné4 resetované bloky duben2023–září2026 a souvislý běh. Uvést čisté P/L,
PF,obchody,MTM DD,intrabar mez,kladné bloky a denní blokový bootstrap.
Neinterpolovat neověřený break-even: uvést pouze interval mezi testovanými
úrovněmi, pokud dojde ke změně znaménka. Není zaručena monotónnost mimo grid.
Porovnat scale1 s původními výsledky a V49 scale2 s uloženým stresem.
Audit ledgerů a uložená úplná evidence všech60 simulací.

Neměnit přijímací brány, nepropagovat levnější hypotetický scénář do PAPER.
Již prohlédnutá vývojová data,žádné nové OOS,intervaly bez korekce na výběr.
Rok2022 se znovu nehodnotí,rok2021 se neotevírá. Žádné nové nasazení.
