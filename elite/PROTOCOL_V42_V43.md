# V42–V43: impuls, uklidnění a potvrzení

Pevný protokol před výsledky, žádná optimalizační mřížka. Test hypotézy,
že čekání po velkém pohybu omezí nákup bezprostředně při cenovém šoku.
V42 pokračování po růstovém impulsu; V43 zotavení po poklesu. Příbuznost
s dřívějšími průrazy/obraty přiznáváme; nejde o nezávislé statistické objevy.

Hodinové UTC svíčky,60 hodin rozehřátí. Impuls má tělo alespoň2×ATR14
z předchozích14 hodin (impuls sám není v ATR) a close v horních20 % rozpětí
pro V42, dolních20 % pro V43. Jediný čekající impuls se uchová nejvýše12h;
nové low pod jeho low jej ruší. Bez překreslování, bez současných setupů.

Vstup nejdříve4h po impulsu: předchozí3 kompletní hodiny mají souhrnné
rozpětí nejvýše polovinu impulsu a low neklesá pod low impulsu.
Aktuální close musí překonat high těchto3 hodin. V42 navíc požaduje jejich
low nad nebo na středu impulsu, V43 aktuální close nad středem impulsu.
Setup se spotřebuje i tehdy, když účet již drží jiný obchod. Při zrušení
může aktuální hodina založit nový impuls, nikdy jej ihned zobchodovat.

Stop vzdálenost max(close−low posledních3 hodin,1,5×zmrazené ATR před impulsem).
Vzdálenost aplikována od skutečné vstupní ceny; není zaručen stop přesně
na low při gapu. Cíl2×stop, časový výstup72h. Signál až na uzavřené hodině,
provedení následující5m open; žádný BTC filtr. Stop/target kontrolovány5m.

Spot LONG, bez páky, účet10 000 USDT, riziko0,5 %, alokace35 %; fee0,1 %,
skluz0,03 %, halfspread0,01 % na stranu. Stres dvojnásobek všech nákladů.
Vývoj duben2023–září2026: původní4 resetované bloky a souvislý běh.
Původní brány:3/4 kladné bloky,60 obchodů, PF>=1,2, DD<=10 %,
intrabar<=12 %, kladný stres a dolní95% bootstrap mez denního P/L nad0.
Po výsledcích lze pro vysvětlení spočítat nulové náklady a koncentraci
v nejlepších obchodech; neslouží k přijetí ani změně pravidel.

Všechna vývojová období opakovaně použita, intervaly nejsou opravené na43
variant. Rok2022 prohlédnutý po V38. Rok2021 tento běh neotevírá.
Žádný vývojový výsledek neopravňuje k PAPER/LIVE bez dalšího ověření.
Ostatní boty a jejich nasazení se nemění.
