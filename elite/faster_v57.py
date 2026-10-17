"""Fixed faster-clock variants of V56; keep V56 itself unchanged."""
from dataclasses import replace
from elite.research_engine import aggregate,validate
from elite.adaptive_v56 import signals,decisions as baseline


def decisions(rows,name):
    if name not in ('v57','v58'):raise ValueError('unknown candidate')
    validate(rows)
    count={'v57':12,'v58':3}[name]
    return {i:replace(d,max_bars=84*count) for i,d in signals(aggregate(rows,count)).items()}


def prepare(rows,btc=None):
    return {'v57':decisions(rows,'v57'),'v58':decisions(rows,'v58'),
            'v56_control':baseline(rows)}


def frequency_failures(periods,days):
    # Count completed trades per block; average frequency is not a weekly guarantee.
    return ['below_one_trade_per_week_'+p for p in periods
            if periods[p]['base']['trades']*7 < days[p]]
