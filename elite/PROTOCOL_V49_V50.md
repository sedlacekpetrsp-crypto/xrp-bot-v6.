# V49–V50: pevné denní rozpětí UTC

Předem zvolená hypotéza: prvních6 hodin dne vytvoří referenční rozpětí pro
pozdější průraz nebo jeho odmítnutí. UTC není odvozeno z optimalizace času.
Nejde o tvrzení, že krypto má oficiální otevírací seanci; obchoduje nepřetržitě.
Příbuznost s dřívějšími průrazy/obraty přetrvává. Žádná mřížka časů/prahů.

Range high/low z kompletních hodin00:00–06:00 UTC. Neúplný první den se
přeskakuje. Šířka musí být1–6 % close v05:59:59 (na5m datech close05:55).
Signální hodiny začínají06:00 až21:00, vstupy tedy07:00 až22:00 UTC.
Maximálně jeden způsobilý vstupní signál za den; po splnění se den spotřebuje
nezávisle na stavu účtu. Pravidlo platí zvlášť pro každou variantu.

V49: předchozí hodinový close<=range high, aktuální close>range high.
Stop vzdálenost1×šířka, cíl2×šířka; target/close alespoň2 %.
V50: low signální hodiny<range low<close. Stop close−low signální hodiny
+0,1×šířka range; cílová vzdálenost range high−close. Vyžadováno target>=2×stop
a target/close>=2 %. Žádný nákup samotného poklesu bez návratu nad low range.
V obou případech vzdálenosti aplikovány od skutečného fill; gap/slippage
může posunout skutečné cenové úrovně vůči range.

Vstup další5m open po uzavřené hodině, stop/target kontrolovány5m, časový
výstup nejpozději další UTC půlnoc open (případně dřívější hranice testu).
Bez trendových/BTC filtrů a bez přípravných dnů; kompletní ranní range
stačí k výpočtu. Účet10 000 USDT, spot LONG bez páky, riziko0,5 %, alokace35 %.
Fee0,10 %, skluz0,03 %, halfspread0,01 % na stranu; stres dvojnásobek.

Původní4 vývojové bloky duben2023–září2026 a souvislý běh. Neměnné brány:
3/4 kladné bloky,60 obchodů, PF>=1,2, DD<=10 %, intrabar<=12 %, kladný stres
a dolní95% bootstrap mez denního P/L nad0. Diagnostika nulových nákladů,
výstupních důvodů a koncentrace po výsledku nesmí měnit přijetí.

Všechna vývojová data již prohlédnutá, intervaly bez korekce na50 verzí.
Rok2022 prohlédnut po V38; rok2021 se neotevírá. Žádné automatické PAPER
schválení, žádné nasazení ani zásah do ostatních botů.
