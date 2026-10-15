# V48: časově oddělená kvalifikace trendu a korekce

Nový navazující pokus na V46, nikoli nezávislá rodina. V46 měla jediný
obchod: aktuální návrat se téměř vylučoval s ER>=0,35. Hypotéza V48:
kvalifikovat silný trend před korekcí, uchovat nejvýše48h a čekat na návrat.
V46 zůstává nezměněným kontrolním během. Parametry před výsledkem pevné.

Hodinová UTC data,200h rozehřátí. Trend: close>SMA168>SMA168 před24h.
ER ze49 předchozích close, ATR14 končí před aktuální hodinou jako ve V46.
1. Pokud trend platí, ER>=0,35 a close>SMA24, založit setup.
2. V pozdější hodině čekat na close<=SMA24. ER se již nepřezkoumává.
3. V další hodině close>SMA24 potvrzuje vstup. Trend musí stále platit.
Setup vyprší při stáří>48h nebo ztrátě trendu. Potvrzení setup spotřebuje
včetně případu, kdy2% filtr nepustí vstup. V jedné hodině nelze zároveň
setup založit, zaznamenat korekci nebo zobchodovat návrat. Jen jeden setup.
Po vypršení či zrušení může stejná hodina založit nový setup bez vstupu.

Stop3ATR, cíl6ATR, target/close>=2 %, max7dnů; výstup při ztrátě trendu.
Vznik/spotřeba setupu nezávisí na tom, zda účet již drží pozici. Indikátorový
stav lze zahřát před hranicí období; účet a pozice se resetují. To není
budoucí informace. Úplné signály jsou kauzální a nemění se po přidání dat.

Spot LONG, bez páky,10 000 USDT, riziko0,5 %, alokace35 %. Fee0,10 %, skluz
0,03 %, halfspread0,01 % na stranu; stres dvojnásobek. Signál z uzavřené
hodiny, další5m open, stop/target kontrolovány5m. Bez BTC filtru.

Původní4 resetované bloky duben2023–září2026 a souvislý běh. Brány neměnné:
3/4 kladné bloky,60 obchodů, PF>=1,2, DD<=10 %, intrabar<=12 %, kladný stres,
dolní95% bootstrap mez denního P/L nad0. Změna počtu obchodů není přijetí.
Následná diagnostika nulových nákladů a výstupů bez ladění parametrů.

Data již prohlédnutá, intervaly bez korekce na48 verzí. Rok2022 prohlédnutý
po V38, rok2021 se neotevírá. Žádný vývojový průchod sám neschvaluje PAPER.
Žádný zásah do ostatních botů ani nasazení.
