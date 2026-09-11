import sys
import urllib.request

URLS = [
    "https://xrp-bot-v8-candle.onrender.com/health",
    "https://xrp-bot-v8-1-candle.onrender.com/",
]

failed = False
for url in URLS:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "render-keepalive/1.0"})
        with urllib.request.urlopen(req, timeout=90) as response:
            code = response.getcode()
            print(f"{url} -> {code}")
            if code < 200 or code >= 400:
                failed = True
    except Exception as exc:
        failed = True
        print(f"{url} -> ERROR: {exc}")

sys.exit(1 if failed else 0)
