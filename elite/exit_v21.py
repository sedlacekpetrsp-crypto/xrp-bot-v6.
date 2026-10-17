"""Fixed V18 entry rules; causal exit ablation only."""
from dataclasses import dataclass
from statistics import mean
from elite.research_engine import Decision,aggregate
from elite.cross_market_v18 import decisions as original_decisions

@dataclass(frozen=True)
class TrailingDecision(Decision):
    trail_distance: float = 0.0

def decisions(xrp,btc,name):
    if name not in ('v21','v22','v23'):
        raise ValueError('unknown exit candidate')
    original=original_decisions(xrp,btc,'v18')
    bars=aggregate(btc,12)
    weak={bars[k][0]:bars[k][4]<mean(b[4] for b in bars[k-167:k+1]) for k in range(200,len(bars))}
    return {i:TrailingDecision(d.stop_distance,d.target_distance,
                d.exit or (name in ('v22','v23') and weak[i]),d.max_bars,
                d.stop_distance if name in ('v21','v23') else 0)
            for i,d in original.items()}
