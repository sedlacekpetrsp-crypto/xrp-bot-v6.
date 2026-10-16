# ELITE: audit simulátoru a oprava vstupů,16.10.2026

Opravena skutečná mezera v ochraně vstupů simulátoru. Ručně vypočtené
účetní příklady neukázaly chybu účtování. V kontrolovaných historických
bězích oprava nezměnila žádný obchod ani denní equity. Nelze ji tedy
vydávat za odstranění příčiny ztrátovosti strategie.
Žádný kandidát pro PAPER, žádné nasazení ani změna ostatních botů.

## Nález a oprava

Datový loader již kontroloval checksumy,úplné měsíce,OHLC a5m kadenci.
Samotné simulate() však tuto ochranu nevynucovalo, takže přímé volání
mohlo přijmout neplatnou řadu. Spotřebované pokyny také neměly přísnou
kontrolu: NaN/nekonečno,záporná vzdálenost,neplatný časový limit či textový
příznak výstupu mohly být tiše ignorovány nebo vyhodnoceny jinak, než bylo zamýšleno.

Před opravou test odmítnutí selhal pro3 vadné tržní řady a9 vadných pokynů.
Záznam `before_fix.json`. Oprava přidává na vstup simulate() validaci celé
řady a před použitím každého signálu validaci konečných nezáporných vzdáleností
stop/target/trailing,celočíselného nezáporného max_bars a bool exit.
Při vadě nastane ValueError; nic se neopravuje odhadem.

Fill logika, pořadí stop/target, riziko0,5 %, alokace35 %, náklady a brány
zůstávají beze změny. Kontrola celé řady při každé simulaci přidává práci;
byla zvolena kvůli bezpečnému samostatnému API, bez neověřené rychlé výjimky.
Změna na větvi `elite-research-v1`, commit
`22c865c19e3509b43ac27dd8854be466e4978067`.

## Nezávislé účetní příklady

Šest fixtures prošlo již před opravou. Neodvozují očekávání z výsledku
simulátoru: poplatkové příklady používají explicitní Decimal cashbook.

- Nákup100,stop90,cíl110 a1% fee: risk50/11,9 jednotek, čistý výnos7,9 na jednotku.
- Velmi těsný stop a následný gap:35% alokační strop omezí pozici na35 jednotek;
  gap100→80 realizuje −700. Plánované riziko negarantuje limit ztráty při gapu.
- Poplatky,skluz i spread na obou stranách plochého obchodu: přesná shoda
  čistého výsledku a záporných nákladů s desetinným výpočtem.
- Gap nad targetem plněn konzervativně na targetu, bez nového vstupu ve stejné svíčce.
- Časový výstup na očekávaném dalším open; signál poslední svíčky nemůže zpětně vstoupit.
- Propad otevřené pozice počítán z hodnoty likvidace; denní závěr souhlasí s účtem.

Původní testy dále pokrývají stop před targetem při dotyku obou v jedné svíčce,
trailing z dokončeného baru, reset overlayů a další případy. Po opravě126 testů prošlo.

## Úplné historické porovnání

Stejná XRP/BTC data duben2023–září2026, šest souvislých replayů:

| Strategie | Base obchodů | Stres obchodů | Celá evidence |
|---|---:|---:|---|
| V18 | 97 | 97 | Přesná shoda |
| V38 | 87 | 87 | Přesná shoda včetně pauz |
| V49 | 541 | 541 | Přesná shoda |

Celkem1450 obchodů. Porovnány celé ledgery, všechny denní body equity,
souhrnné metriky a události overlaye; nejen celkový zisk. Referenční archivy
a jejich SHA256 i kanonické hashe replayů jsou v souhrnu.
Na skutečných datech V18 a V49 navíc prošla shoda prefixu z poloviny historie
plus5 svíček s celým souborem. Neúplná agregovaná hodina nevytvořila předčasný signál.

## Omezení a další rozhodnutí

Toto není důkaz absence všech chyb. Historický replay zahrnul3 varianty,
ne všech50; exact replay potvrzuje neměnnost po opravě, sám nepotvrzuje
správnost původního modelu. Tu v uvedených případech kontrolují ruční fixtures.
Prefix kontroluje vybrané signály, ne všechny možné budoucí implementace.
5m OHLC neposkytuje skutečné pořadí ticků, hloubku knihy, latenci či částečná
plnění. Intrabar DD zůstává konzervativní mezí, nikoli měřeným tickovým průběhem.

Staré protokoly/hash guards se nemění. V38 challenge s novým hashem enginu
správně odmítne vydávat nový kód za původní; reprodukce starého běhu vyžaduje
původní zmrazený commit. Tento audit neotevřel2021 ani2022 a není nové OOS.
Výsledky neposkytují důvod snižovat náklady nebo zmírnit přijímací podmínky.

Evidence `results/20261016_engine_audit`: `before_fix.json`, `tests.txt`,
`summary.json`. Reprodukce: `python -m elite.engine_audit --cache CACHE --out OUT`.

## Odchylka prostředí a její ověření

První CI běh v Python3.11 zastavil přesné porovnání V49 stress. Diagnostický
běh ukázal jediné rozdílné pole: PF0,6442399315550612 oproti uloženému
0,6442399315550604, rozdíl7,77e−16. Obchody,denní equity,náklady a ostatní
metriky zůstaly totožné. Sekvenční součet původního ledgeru reprodukoval
hodnotu z3.11, viz `summation_diagnostic.json`.

[První zastavený běh](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38852563856)
a [diagnostický běh](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38852767644)
jsou zachovány. CI audit byl sjednocen s Python3.12, ve kterém vznikla
lokální reference. Nebyla přidána tolerance ani zaokrouhlení, přesná
kontrola všech polí zůstává. Skutečná verze runtime je nyní v souhrnu.
Zdrojový commit sjednocení `ebe3529b24c7c0c98d3cd35c2f3989bc55f7881c`.

[Závěrečný CI audit](https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/38852892693)
prošel:126 testů a všech6 plných porovnání s přesnou shodou. Oprava i
reprodukce jsou ověřené lokálně a na GitHubu. Nejde o ověření ziskovosti.
