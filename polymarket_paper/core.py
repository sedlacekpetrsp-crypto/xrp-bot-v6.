"""PAPER simulace párové strategie na Polymarket krypto trzích Up/Down.

Žádné skutečné objednávky. Vše se jen počítá proti veřejné knize objednávek.

Dvě strategie:
  A) instant_pair  – koupit Up i Down hned jako taker, jen když součet cen
                     včetně poplatků < 1 - min_edge (čistá arbitráž).
  B) leg_in        – styl z tweetu: kupovat stranu, která je „levná“,
                     a postupně dorovnávat druhou stranu, pokud průměrná
                     cena páru zůstává < target_pair_cost. Nespárované
                     kusy nesou směrové riziko až do vyhodnocení.

Konzervativní předpoklady (simulace je spíš optimistická, viz README):
  - plnění za zobrazené asky (bez latence, bez fronty, bez konkurence),
  - taker poplatek fee = shares * rate * p * (1 - p) z feeSchedule trhu,
  - držení do vyhodnocení, výplata 1 USDC za vítězný kus.
"""
from __future__ import annotations

from dataclasses import dataclass, field

UP, DOWN = 0, 1


def taker_fee(shares: float, price: float, rate: float) -> float:
    """Polymarket taker fee: C * rate * p * (1 - p)."""
    return shares * rate * price * (1.0 - price)


def parse_asks(book: dict) -> list[tuple[float, float]]:
    """Vrátí asky seřazené od nejlevnějšího jako [(price, size)]."""
    asks = [(float(a["price"]), float(a["size"])) for a in book.get("asks", [])]
    asks.sort(key=lambda x: x[0])
    return [a for a in asks if a[1] > 0]


def parse_bids(book: dict) -> list[tuple[float, float]]:
    """Vrátí bidy seřazené od nejdražšího jako [(price, size)]."""
    bids = [(float(b["price"]), float(b["size"])) for b in book.get("bids", [])]
    bids.sort(key=lambda x: -x[0])
    return [b for b in bids if b[1] > 0]


def sell_proceeds(bids: list[tuple[float, float]], shares: float, rate: float):
    """Výnos z prodeje `shares` kusů do bidů po taker poplatku.

    Když bidy nestačí, prodá se jen to, co kniha unese: vrací
    (prodané_kusy, výnos_usdc). Prázdná kniha -> (0, 0).
    """
    left, got = shares, 0.0
    for price, size in bids:
        take = min(left, size)
        got += take * price - taker_fee(take, price, rate)
        left -= take
        if left <= 1e-9:
            break
    return shares - max(left, 0.0), got


def buy_cost(asks: list[tuple[float, float]], shares: float, rate: float):
    """Projde knihu a spočte cenu nákupu `shares` kusů včetně poplatku.

    Vrací (celková_cena_usdc, průměrná_cena_včetně_poplatku) nebo None,
    když kniha nemá dost likvidity.
    """
    left, total = shares, 0.0
    for price, size in asks:
        take = min(left, size)
        total += take * price + taker_fee(take, price, rate)
        left -= take
        if left <= 1e-9:
            return total, total / shares
    return None


@dataclass
class Position:
    shares: list = field(default_factory=lambda: [0.0, 0.0])
    cost: list = field(default_factory=lambda: [0.0, 0.0])
    fills: int = 0
    gross_cost: float = 0.0     # součet všech nákupů (pro výnos z nákladu)
    realized: float = 0.0       # zisk/ztráta z prodaných kusů
    memo: dict = field(default_factory=dict)  # stav strategie pro tento trh

    def avg(self, side: int) -> float:
        return self.cost[side] / self.shares[side] if self.shares[side] else 0.0

    @property
    def matched(self) -> float:
        return min(self.shares)

    def add(self, side: int, shares: float, cost: float) -> None:
        """Nákup: shares > 0, cost = zaplaceno. Prodej: shares < 0, cost = -výnos."""
        self.fills += 1
        if shares >= 0:
            self.shares[side] += shares
            self.cost[side] += cost
            self.gross_cost += cost
            return
        n = min(-shares, self.shares[side])
        basis = self.avg(side) * n
        self.shares[side] -= n
        self.cost[side] -= basis
        self.realized += -cost - basis

    def settle(self, winner: int) -> float:
        """PnL v USDC po vyhodnocení trhu (včetně dřívějších prodejů)."""
        return self.shares[winner] * 1.0 - sum(self.cost) + self.realized


@dataclass
class InstantPair:
    """Strategie A: okamžitý nákup obou stran, když pár stojí < 1 - edge."""
    name: str = "instant_pair"
    clip: float = 10.0        # kusů na stranu na jeden obchod
    min_edge: float = 0.01    # minimální zisk na pár po poplatcích
    max_shares: float = 200.0  # strop na stranu v jednom trhu

    def on_book(self, pos: Position, asks_up, asks_dn, rate: float):
        if pos.shares[UP] + self.clip > self.max_shares:
            return []
        up = buy_cost(asks_up, self.clip, rate)
        dn = buy_cost(asks_dn, self.clip, rate)
        if not up or not dn:
            return []
        if up[1] + dn[1] <= 1.0 - self.min_edge:
            return [(UP, self.clip, up[0]), (DOWN, self.clip, dn[0])]
        return []


@dataclass
class LegIn:
    """Strategie B: kupovat levnou stranu, dorovnávat do páru < target."""
    name: str = "leg_in"
    clip: float = 10.0
    cheap: float = 0.45            # strana je „levná“ pod touto cenou
    target_pair_cost: float = 0.97  # cílová průměrná cena páru vč. poplatků
    max_imbalance: float = 40.0    # max nespárovaných kusů
    max_shares: float = 200.0
    stop_new_legs_sec: float = 60.0  # posledních N s nové nespárované nákupy ne

    def on_book(self, pos: Position, asks_up, asks_dn, rate: float,
                secs_left: float = 1e9):
        books = {UP: asks_up, DOWN: asks_dn}
        for side in (UP, DOWN):
            other = 1 - side
            if pos.shares[side] + self.clip > self.max_shares:
                continue
            q = buy_cost(books[side], self.clip, rate)
            if not q:
                continue
            new_avg = (pos.cost[side] + q[0]) / (pos.shares[side] + self.clip)
            imbalance_after = pos.shares[side] + self.clip - pos.shares[other]
            # 1) dorovnání: snižuje nespárovanou pozici a pár je pod cílem
            if pos.shares[other] - pos.shares[side] >= self.clip:
                if new_avg + pos.avg(other) <= self.target_pair_cost:
                    return [(side, self.clip, q[0])]
                continue
            # 2) nová noha: strana je levná a nerozjede to nerovnováhu
            if secs_left < self.stop_new_legs_sec:
                continue
            if q[1] <= self.cheap and imbalance_after <= self.max_imbalance:
                if pos.shares[other] == 0 or new_avg + pos.avg(other) <= self.target_pair_cost:
                    return [(side, self.clip, q[0])]
        return []


@dataclass
class InstantPairConfirmed(InstantPair):
    """Strategie A s kontrolou reality: arbitráž musí vydržet 2 snímky po sobě.

    Příležitost, která zmizí do dalšího čtení knihy (~4 s), by reálně
    sebral rychlejší bot. Tahle varianta ji proto nepočítá.
    """
    name: str = "instant_pair_confirmed"

    def on_book(self, pos: Position, asks_up, asks_dn, rate: float):
        orders = InstantPair.on_book(self, pos, asks_up, asks_dn, rate)
        seen = pos.memo.get("edge_seen", False)
        pos.memo["edge_seen"] = bool(orders)
        return orders if seen else []


@dataclass
class LegInV2:
    """Strategie B v2: skládání páru s pevnou kontrolou rizika.

    Ze 2 782 trhů verze 1 (26.–28. 11. 2026): nespárovaná strana prohrála
    v 1 904 z 1 917 trhů. Pár se totiž dokončí hlavně tehdy, když by první
    noha stejně vyhrála; když prohrává, druhá strana nezlevní. Proto:
      - nanejvýš JEDNA nespárovaná dávka (žádné přikupování padající strany),
      - nová noha jen při vyrovnané pozici a jen když zbývá dost času,
      - nespárovanou nohu po `max_wait_sec` nebo před koncem prodat do bidů,
        nikdy ji nedržet do vyhodnocení.
    """
    name: str = "leg_in_v2"
    clip: float = 10.0
    cheap: float = 0.45
    min_price: float = 0.25          # pod tím už trh „rozhodl“, nesázet
    target_pair_cost: float = 0.97
    max_shares: float = 200.0
    stop_new_legs_sec: float = 120.0
    max_wait_sec: float = 60.0
    force_exit_sec: float = 45.0

    def on_book(self, pos: Position, asks_up, asks_dn, rate: float,
                secs_left: float = 1e9, bids_up=None, bids_dn=None):
        asks = {UP: asks_up, DOWN: asks_dn}
        bids = {UP: bids_up or [], DOWN: bids_dn or []}
        diff = pos.shares[UP] - pos.shares[DOWN]
        if abs(diff) > 1e-9:
            heavy = UP if diff > 0 else DOWN
            light = 1 - heavy
            n = abs(diff)
            q = buy_cost(asks[light], n, rate)
            if q and pos.avg(heavy) + q[1] <= self.target_pair_cost:
                pos.memo.pop("leg_opened_at", None)
                return [(light, n, q[0])]
            waited = pos.memo.get("leg_opened_at", secs_left) - secs_left
            if waited >= self.max_wait_sec or secs_left < self.force_exit_sec:
                sold, got = sell_proceeds(bids[heavy], n, rate)
                if sold > 0:
                    if sold >= n - 1e-9:
                        pos.memo.pop("leg_opened_at", None)
                    return [(heavy, -sold, -got)]
            return []
        if secs_left < self.stop_new_legs_sec:
            return []
        for side in (UP, DOWN):
            if pos.shares[side] + self.clip > self.max_shares:
                continue
            q = buy_cost(asks[side], self.clip, rate)
            if q and self.min_price <= q[1] <= self.cheap:
                pos.memo["leg_opened_at"] = secs_left
                return [(side, self.clip, q[0])]
        return []
