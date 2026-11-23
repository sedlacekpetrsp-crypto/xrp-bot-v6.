"""Ex-ante G1 precision denominator feasibility; no model predictions or performance data."""
from math import isfinite, sqrt


def wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    """Two-sided 95% Wilson lower confidence bound for a binomial proportion."""
    if isinstance(successes, bool) or isinstance(trials, bool) or not isinstance(successes, int) or not isinstance(trials, int):
        raise ValueError("integer counts required")
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("invalid counts")
    if not isfinite(z) or z <= 0:
        raise ValueError("invalid z")
    p = successes / trials
    d = 1 + z * z / trials
    return (p + z*z/(2*trials) - z*sqrt(p*(1-p)/trials + z*z/(4*trials*trials))) / d


def minimum_successes(trials: int, threshold: float) -> int | None:
    """Minimum successes whose Wilson lower bound exceeds threshold; None if impossible."""
    if isinstance(trials, bool) or not isinstance(trials, int) or trials <= 0:
        raise ValueError("invalid trials")
    if not isfinite(threshold) or not 0 <= threshold < 1:
        raise ValueError("invalid threshold")
    for successes in range(trials + 1):
        if wilson_lower(successes, trials) > threshold:
            return successes
    return None


def preflight_denominators(positive_episodes: int, alert_episode_budget: int) -> dict:
    """Check separate recall/precision denominators before any predictions exist.

    Budget is a pre-registered hypothetical alert count, not observed alerts.
    """
    recall = minimum_successes(positive_episodes, 0.5)
    precision = minimum_successes(alert_episode_budget, 0.6)
    return {
        "positive_episode_count": positive_episodes,
        "alert_episode_budget": alert_episode_budget,
        "minimum_recall_hits": recall,
        "minimum_precision_true_alerts": precision,
        "precision_possible": precision is not None,
        "status": "EX_ANTE_ONLY",
    }
