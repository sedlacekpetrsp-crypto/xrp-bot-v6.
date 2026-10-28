"""Manual one-shot PAPER data capture; never places orders or starts a daemon.

Usage: python collect_snapshot.py MARKET_SLUG OUTPUT.jsonl
Run under an explicitly configured external scheduler only if desired.
Stores request/receipt times and failures. Never substitutes fake quotes.
"""
import concurrent.futures
import json
import sys
import time
import urllib.parse
import urllib.request


def get(url):
    record={'url':url,'requested_at':time.time()}
    try:
        with urllib.request.urlopen(url,timeout=15) as response:
            record.update(status=response.status,data=json.load(response))
    except Exception as exc:
        record['error']=str(exc)
    record['received_at']=time.time()
    return record


def capture(slug):
    if not slug.startswith('xrp-updown-5m-') or not slug.rsplit('-',1)[1].isdigit():
        raise ValueError('Expected exact XRP five-minute market slug')
    start=int(slug.rsplit('-',1)[1])
    gamma=get('https://gamma-api.polymarket.com/markets?'+urllib.parse.urlencode({'slug':slug}))
    result={'mode':'PAPER','slug':slug,'window_start':start,'gamma':gamma}
    markets=gamma.get('data',[])
    matches=[m for m in markets if isinstance(m,dict) and m.get('slug')==slug] if isinstance(markets,list) else []
    if len(matches)!=1:
        result['usable']=False;result['reason']='Exact market unavailable';return result
    m=matches[0]
    decode=lambda x:json.loads(x) if isinstance(x,str) else x
    outcomes,tokens=decode(m['outcomes']),decode(m['clobTokenIds'])
    if len(outcomes)!=len(tokens) or outcomes.count('Up')!=1:
        raise ValueError('Ambiguous outcome-token mapping')
    token=tokens[outcomes.index('Up')]
    urls=['https://clob.polymarket.com/book?'+urllib.parse.urlencode({'token_id':token}),
          'https://data-api.binance.vision/api/v3/depth?symbol=XRPUSDT&limit=5']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        result['observations']=list(pool.map(get,urls))
    result['up_token']=token
    result['requests_succeeded']=all(x.get('status')==200 for x in result['observations'])
    result['captured_in_window']=all(start<=x['requested_at']<=x['received_at']<start+300 for x in result['observations'])
    # Successful responses still need quote-schema, spread and freshness audit.
    result['usable']=False
    result['reason']='Raw capture only; validate before admitting to backtest'
    return result


if __name__=='__main__':
    result=capture(sys.argv[1])
    with open(sys.argv[2],'a') as output:
        output.write(json.dumps(result)+'\n')
    print(json.dumps({'slug':result['slug'],'usable':result['usable'],'reason':result['reason']}))
