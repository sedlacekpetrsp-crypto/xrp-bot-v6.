"""One entry attempt per consecutive hourly XRP breakout episode."""
from elite.research_engine import Decision,decisions as raw_decisions
from elite.cross_market_v18 import decisions as baseline


def gate(base,raw):
    if base.keys()!=raw.keys():raise ValueError('signal clock mismatch')
    out={};previous_breakout=False
    for index in sorted(raw):
        d=base[index];breakout=raw[index].stop_distance>0
        out[index]=Decision(d.stop_distance if breakout and not previous_breakout else 0,
                            d.target_distance,d.exit,d.max_bars)
        previous_breakout=breakout
    return out


def prepare(rows,btc):
    base=baseline(rows,btc,'v18');raw=raw_decisions(rows,'v5')
    return {'v51':gate(base,raw),'v18_control':base}
