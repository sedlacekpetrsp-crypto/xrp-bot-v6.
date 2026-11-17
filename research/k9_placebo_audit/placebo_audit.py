"""Independent fail-closed structural audit of K9 placebo minute selection.

No market data, P/L, strategy signals or performance evaluation is performed.
"""
from collections import Counter
from collections.abc import Iterable
from datetime import datetime


def audit_placebo_minutes(signals: Iterable[tuple[str, str, int]],
                          placebos: Iterable[tuple[str, str, int]],
                          *, min_clean_support: int = 1) -> dict:
    """Keys: (asset, UTC YYYY-MM-DDTHH hour, minute 0..59).

    A placebo is contaminated when it equals ANY signal key, not just the
    signal against which it was matched. Does not assert exchange coverage.
    """
    if type(min_clean_support) is not int or min_clean_support < 1:
        raise ValueError('min_clean_support must be positive integer')

    def normalized(rows, label):
        output = []
        for key in rows:
            if not isinstance(key, tuple) or len(key) != 3:
                raise ValueError(f'{label}: expected 3-tuple')
            asset, hour, minute = key
            if (not isinstance(asset, str) or not asset.strip()
                    or not isinstance(hour, str) or len(hour) != 13
                    or hour[10] != 'T' or type(minute) is not int
                    or not 0 <= minute < 60):
                raise ValueError(f'{label}: invalid key')
            try:
                parsed = datetime.strptime(hour, '%Y-%m-%dT%H')
            except ValueError as exc:
                raise ValueError(f'{label}: invalid UTC hour') from exc
            if parsed.strftime('%Y-%m-%dT%H') != hour:
                raise ValueError(f'{label}: noncanonical UTC hour')
            output.append(key)
        return output

    signal_keys = set(normalized(signals, 'signals'))
    placebo_keys = normalized(placebos, 'placebos')
    contaminated = [key for key in placebo_keys if key in signal_keys]
    clean = [key for key in placebo_keys if key not in signal_keys]
    duplicates = sum(n - 1 for n in Counter(placebo_keys).values() if n > 1)
    return {
        'verdict': 'PASS' if not contaminated and not duplicates and len(clean) >= min_clean_support else 'INCONCLUSIVE',
        'signal_keys': len(signal_keys),
        'placebo_draws': len(placebo_keys),
        'contaminated_draws': len(contaminated),
        'duplicate_draws': duplicates,
        'clean_draws': len(clean),
        'min_clean_support': min_clean_support,
    }
