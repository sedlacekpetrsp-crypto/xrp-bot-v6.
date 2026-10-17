# V46–V47: navazující režimové experimenty, před výsledkem

Příbuznost s V9/V10/V11 je záměrně uvedena: nejde o nové nezávislé rodiny.
V46 testuje hodinový návrat nad24h průměr v účinném rostoucím trendu;
V47 návrat po vybočení pod pásmo v kolísavém trhu. Parametry pevné bez mřížky.

Hodinové UTC svíčky,200 hodin rozehřátí. Efficiency ratio z49 předchozích
close: absolutní změna za48h dělená součtem absolutních změn, při nulové
cestě0. ATR14 rovněž končí před aktuální hodinou.
V46: ER>=0,35; close nad SMA168 a SMA168 nad hodnotou před24h; předchozí
close<=předchozí SMA24, aktuální close>aktuální SMA24. Stop3ATR, cíl6ATR,
výstup při ztrátě trendu, nejvýše7dnů. Jde o krátký návrat v delším trendu.
V47: ER<=0,2; aktuální low pod předchozí SMA24−2ATR, close nad touto hranicí,
ale pod předchozí SMA24. Stop2ATR, cíl4ATR, výstup close>=aktuální SMA24,
nejvýše2dny. Nejde o nákup, dokud cena zůstává pod pásmem.

Obě vyžadují poměr vzdálenosti cíle k signal close alespoň2 %. To je hrubý
filtr rozsahu, nikoli slib2% zisku: stop nebo signál může obchod ukončit dříve.
Žádný BTC filtr. Spot LONG, bez páky, účet10 000 USDT, riziko0,5 %, alokace35 %.
Fee0,10 %, skluz0,03 %, halfspread0,01 % na stranu; stres dvojnásobek.
Signál z dokončené hodiny, provedení další5m open, stop/target sledovány5m.

Původní4 resetované vývojové bloky duben2023–září2026 a souvislý běh.
Brány:3/4 kladné bloky,60 obchodů, PF>=1,2, DD<=10 %, intrabar<=12 %, kladný
stres a dolní95% bootstrap mez denního P/L nad0. Následná diagnostika
nulových nákladů a koncentrace nesmí změnit pravidla ani přijetí.

Všechna vývojová období již použitá, intervaly bez korekce na47 verzí.
Rok2022 již prohlédnut po V38. Rok2021 se neotevírá. Bez další validace
žádné schválení PAPER/LIVE. Ostatní boty se nemění.
