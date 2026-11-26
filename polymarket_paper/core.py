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

    def avg(self, side: int) -> float:
        return self.cost[side] / self.shares[side] if self.shares[side] else 0.0

    @property
    def matched(self) -> float:
        return min(self.shares)

    def add(self, side: int, shares: float, cost: float) -> None:
        self.shares[side] += shares
        self.cost[side] += cost
        self.fills += 1

    def settle(self, winner: int) -> float:
        """PnL v USDC po vyhodnocení trhu."""
        return self.shares[winner] * 1.0 - sum(self.cost)


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
