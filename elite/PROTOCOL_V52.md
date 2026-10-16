# V52 — potvrzené dvojité dno, zmrazení před výsledky

Nová cenová hypotéza: dvě blízká lokální minima a následný průraz vrcholu
mezi nimi mohou potvrdit obrat. Nejde o filtr V18. V18 pouze kontrola.
Žádný BTC filtr, žádný týdenní trendový filtr, žádné ladění po výsledku.

Kompletní UTC hodiny. Striktní pivot low je nižší než dvě předchozí a dvě
následující hodinová minima; dostupný teprve při uzavření druhé následující
hodiny. Porovnat dva poslední potvrzené pivoty, vzdálenost6–48 hodin,
rozdíl minim <=0,5 ATR14 známého při potvrzení druhého pivotu. Neckline je
maximum high mezi pivoty, výška nad nižším dnem alespoň1 ATR.

Každý nový potvrzený pivot ruší staré čekající nastavení. Platnost nového
nastavení24 hodin od potvrzení včetně krajní hodiny. Vstup pouze při
překřížení close z<=neckline na>neckline po potvrzení nebo v jeho hodině.
Stop je nižší minimum minus0,5 ATR z okamžiku potvrzení. Zásah této úrovně
již v signální hodině nastavení ruší. Stop distance = signální close−stop;
simulátor jej ukotví k následující vstupní ceně, tedy při gapu není absolutní
stop cena garantována. Cíl2×stop distance, minimálně2 % signální ceny.
Jeden pokus na nastavení; zamítnutí malého cíle pokus také spotřebuje.
Time exit72 hodin (864 pětiminutových barů). Bez dalších výstupů.

Stejný engine, kapitál10000 USDT, riziko0,5 %, alokace max35 %, jedna LONG
spot pozice, bez páky. Fee0,1 %, slip0,03 %, half-spread0,01 % každá strana;
stress vše2×. Vyhodnocení stejných čtyř vývojových období2023/2024H1/2024H2/
2025–26 a souvislého běhu. Minimálně3/4 kladné bloky,60 obchodů,PF>=1,2,
close DD<=10 %, intrabar bound<=12 %, kladný stress P/L a kladná dolní95%
mez7denního block bootstrap denního P/L. Žádné zmírnění bran.

2023–26 jsou vývojová data po nejméně51 verzích; statistika není opravena
na mnohonásobné hledání. Rok2022 již spotřebován V38;2021 rezervován.
Nový kandidát musí projít nejprve vývojem, pak zvlášť zmrazenou nezávislou
validací. Žádný automatický PAPER ani LIVE. Ostatní boty beze změny.

Rozpracovaný dodatečný audit V18 byl odložen před výpočtem na základě
uživatelova požadavku zaměřit další práci na nové strategie.
