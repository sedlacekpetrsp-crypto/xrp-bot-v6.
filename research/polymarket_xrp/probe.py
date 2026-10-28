"""Read-only public API probe. No credentials, orders or paid dependencies."""
import concurrent.futures
import datetime
import json
import urllib.request
from pathlib import Path

TOKEN = '63226735892907790703332133520255411605971299627832374043768521608646536167274'
QUERY = f'market={TOKEN}&startTs=1773952800&endTs=1773953100&fidelity=1'
URLS = [
    'https://data-api.binance.vision/api/v3/klines?symbol=XRPUSDT&interval=5m&limit=2',
    'https://gamma-api.polymarket.com/markets?slug=xrp-updown-5m-1773952800',
    'https://clob.polymarket.com/prices-history?' + QUERY,
    'https://data-api.polymarket.com/v2/prices-history?' + QUERY,
]


def probe(url):
    result = {'url':url, 'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            result.update(status=response.status, data=json.load(response))
    except Exception as exc:
        result.update(error=str(exc))
    return result


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(probe, URLS))
    output = Path(__file__).with_name('api_probe.json')
    output.write_text(json.dumps(results,indent=2))
    for result in results:
        print(result['url'], result.get('status',result.get('error')))
