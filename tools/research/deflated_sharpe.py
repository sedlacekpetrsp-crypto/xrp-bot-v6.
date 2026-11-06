"""Probabilistic a Deflated Sharpe Ratio (Bailey & López de Prado 2012, 2014).

Výhradně výzkumný nástroj (PAPER). Bez externích závislostí (statistics.NormalDist).
Všechny Sharpe hodnoty jsou NEANUALIZOVANÉ (na periodu výnosů, např. den), pokud
není použit parametr `periods_per_year` u pomocných funkcí.

Použití (rámec v2, bod 2): u každého „prošlo“ spočítat DSR pro validační období,
N = průběžný počet otestovaných variant v STRATEGY_REGISTRY.md; požadavek DSR >= 0,95.

CLI:
  python -m tools.research.deflated_sharpe --equity equity.csv --column equity \
      --n-trials 60 --var-trials 0.0004
  (equity.csv: denní hodnota portfolia; počítají se denní prosté výnosy)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from statistics import NormalDist

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()


def moments(returns):
    """Vrátí (sharpe, skew, kurtosis_nonexcess, T) z řady výnosů na periodu."""
    r = [float(x) for x in returns]
    t = len(r)
    if t < 3:
        raise ValueError("potřeba aspoň 3 výnosy")
    mu = sum(r) / t
    m2 = sum((x - mu) ** 2 for x in r) / t
    if m2 <= 0:
        raise ValueError("nulový rozptyl výnosů")
    sd = math.sqrt(m2)
    skew = sum((x - mu) ** 3 for x in r) / t / sd ** 3
    kurt = sum((x - mu) ** 4 for x in r) / t / m2 ** 2
    # Sharpe s výběrovou směrodatnou odchylkou (ddof=1), jak je obvyklé
    sr = mu / math.sqrt(m2 * t / (t - 1))
    return sr, skew, kurt, t


def probabilistic_sharpe(sr, sr_benchmark, t, skew=0.0, kurt=3.0):
    """PSR = P(skutečný SR > sr_benchmark | odhad sr z t pozorování). kurt = NEexcesní (normální = 3)."""
    if t < 2:
        raise ValueError("t musí být >= 2")
    denom2 = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom2 <= 0:
        raise ValueError("neplatná kombinace momentů (jmenovatel <= 0)")
    z = (sr - sr_benchmark) * math.sqrt(t - 1) / math.sqrt(denom2)
    return _N.cdf(z)


def expected_max_sharpe(n_trials, var_trials):
    """Očekávané maximum SR z n_trials nezávislých pokusů se skutečným SR = 0 a rozptylem var_trials."""
    if n_trials < 1:
        raise ValueError("n_trials >= 1")
    if var_trials < 0:
        raise ValueError("var_trials >= 0")
    if n_trials == 1:
        return 0.0
    a = _N.inv_cdf(1.0 - 1.0 / n_trials)
    b = _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trials) * ((1.0 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe(sr, t, n_trials, var_trials, skew=0.0, kurt=3.0):
    """DSR = PSR proti očekávanému maximu SR z n_trials pokusů."""
    sr0 = expected_max_sharpe(n_trials, var_trials)
    return probabilistic_sharpe(sr, sr0, t, skew, kurt)


def var_from_trial_sharpes(trial_srs):
    s = [float(x) for x in trial_srs]
    if len(s) < 2:
        raise ValueError("potřeba aspoň 2 hodnoty SR pokusů")
    m = sum(s) / len(s)
    return sum((x - m) ** 2 for x in s) / (len(s) - 1)


def annual_to_period(sr_annual, periods_per_year):
    return sr_annual / math.sqrt(periods_per_year)


def dsr_from_returns(returns, n_trials, var_trials):
    sr, skew, kurt, t = moments(returns)
    return {"sharpe_per_period": sr, "skew": skew, "kurtosis": kurt, "T": t,
            "n_trials": n_trials, "var_trials": var_trials,
            "sr0": expected_max_sharpe(n_trials, var_trials),
            "psr_vs_0": probabilistic_sharpe(sr, 0.0, t, skew, kurt),
            "dsr": deflated_sharpe(sr, t, n_trials, var_trials, skew, kurt)}


def _main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--equity", required=True)
    ap.add_argument("--column", default="equity")
    ap.add_argument("--n-trials", type=int, required=True)
    ap.add_argument("--var-trials", type=float, required=True, help="rozptyl SR pokusů (na periodu)")
    a = ap.parse_args()
    with open(a.equity, newline="") as fh:
        eq = [float(row[a.column]) for row in csv.DictReader(fh)]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    print(json.dumps(dsr_from_returns(rets, a.n_trials, a.var_trials), indent=2))


if __name__ == "__main__":
    _main()
