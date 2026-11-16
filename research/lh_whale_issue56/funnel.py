"""Offline signal diagnostic, never simulates trades or performance."""
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lh_whale import closed
from lh_sweep import signal_from_closed_candles

def run(data):
    counts = Counter(valid_5m=0, sweep_reclaim=0, aligned_trend=0, volume_pass=0, setup=0)
    reasons = Counter()
    for row in data['5m']:
        stamp = int(row[6])+1
        if not data['start_ms'] < stamp <= data['end_ms']: continue
        rows = [closed([r for r in data[k] if int(r[6])<stamp][-250:], m, stamp)
                for k,m in [('5m',5),('15m',15),('1h',60)]]
        a,b,c=rows; d={}
        sig=signal_from_closed_candles(*[[float(r[i]) for r in a] for i in (2,3,4,5)],
            [float(r[4]) for r in b],[float(r[4]) for r in c],stop_atr=2.,rr=2.5,diagnostics=d)
        counts['valid_5m']+=1
        swept=d['long_sweep'] or d['short_sweep']
        aligned=(d['long_sweep'] and d['long_trend']) or (d['short_sweep'] and d['short_trend'])
        counts['sweep_reclaim']+=int(swept)
        counts['aligned_trend']+=int(aligned)
        counts['volume_pass']+=int(aligned and d['volume_pass'])
        counts['setup']+=int(sig is not None)
        reasons[d['reason_code']]+=1
    return dict(counts=counts,reasons=reasons,futures_3of3='UNKNOWN: historical PIT observations absent',
                risk_time_guards='UNKNOWN',actual_entries_in_window='UNKNOWN',performance_test=False)

if __name__=='__main__':
    print(json.dumps(run(json.loads(Path(sys.argv[1]).read_text())),indent=2))
