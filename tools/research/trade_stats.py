"""Kolo 10, bod 2: statistická síla obchodních kritérií (PAPER výzkum). Jen diagnostika a návrh pravidla — verdikt
runnerů zatím nemění. Bez libovolných minim počtu obchodů: potřebný vzorek plyne z předem zvolené chybovosti α
a síly 1 − β.

- sign_test_p: jednostranný binomický test „podíl ziskových jednotek > 1/2“ (jednotka = koš/obchod). Nejmenší n,
  při kterém vůbec může projít: n_min = ⌈log2(1/α)⌉ (všechny ziskové); pro α = 0,00625 je to 8.
- stationary_bootstrap_ci: Politis–Romano stationary bootstrap (předem pevná střední délka bloku) pro průměr a PF.
- effective_n: efektivní velikost vzorku z autokorelací (Bartlett, do lagu L).
- concentration: podíl zisku z top-k, kolik nejlepších jednotek stačí odebrat, aby net ≤ 0.
- required_n: n ≈ ((z_{1−α} + z_{1−β}) · CV)² pro test průměru > 0, CV = sd/průměr (normální aproximace).
"""
import math
import random
from statistics import NormalDist


def sign_test_p(x):
    n = len(x)
    k = sum(1 for v in x if v > 0)
    return sum(math.comb(n, j) for j in range(k, n + 1)) / 2 ** n if n else 1.0


def sign_test_min_n(alpha):
    return math.ceil(math.log2(1 / alpha))


def _pf(x):
    g = sum(v for v in x if v > 0)
    l = -sum(v for v in x if v < 0)
    return math.inf if l == 0 and g > 0 else (g / l if l > 0 else float("nan"))


def stationary_bootstrap_ci(x, stat="mean", B=2000, mean_block=5.0, alpha=0.05, seed=12345):
    """Jednostranná dolní mez (1 − α) statistiky stat ∈ {mean, pf}. Pevné seed a délka bloku ⇒ reprodukovatelné."""
    n = len(x)
    if n == 0:
        return None
    f = (lambda s: sum(s) / len(s)) if stat == "mean" else _pf
    rng, p = random.Random(seed), 1.0 / mean_block
    vals = []
    for _ in range(B):
        out, i = [], rng.randrange(n)
        while len(out) < n:
            out.append(x[i])
            i = rng.randrange(n) if rng.random() < p else (i + 1) % n
        vals.append(f(out))
    vals.sort()
    return vals[int(alpha * (B - 1))]


def effective_n(x, max_lag=None):
    n = len(x)
    if n < 3:
        return float(n)
    mu = sum(x) / n
    var = sum((v - mu) ** 2 for v in x) / n
    if var == 0:
        return float(n)
    L = max_lag or max(1, int(round(n ** (1 / 3))))
    s = 0.0
    for k in range(1, min(L, n - 1) + 1):
        rho = sum((x[i] - mu) * (x[i + k] - mu) for i in range(n - k)) / (n * var)
        s += (1 - k / (L + 1)) * rho
    return n / max(1e-9, 1 + 2 * s)


def concentration(x, k=3):
    gains = sorted((v for v in x if v > 0), reverse=True)
    total_g = sum(gains)
    net, removed, srt = sum(x), 0, sorted(x, reverse=True)
    while net > 0 and removed < len(srt):
        net -= srt[removed]
        removed += 1
    return {"top_k_share_of_gains": (sum(gains[:k]) / total_g) if total_g > 0 else None,
            "remove_best_to_flip": removed if sum(x) > 0 else 0}


def required_n(cv, alpha, power=0.8):
    z = NormalDist().inv_cdf
    return math.ceil(((z(1 - alpha) + z(power)) * cv) ** 2)
