import threading
import time
import urllib.request

_TARGET = "https://xrp-bot-v8-candle.onrender.com/health"
_INTERVAL_SECONDS = 300


def _keep_candle_awake():
    # Give the host service time to finish starting before the first request.
    time.sleep(20)
    while True:
        try:
            req = urllib.request.Request(
                _TARGET,
                headers={"User-Agent": "xrp-v81-keepalive/1.0"},
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                print(f"KEEPALIVE V8 CANDLE -> {response.getcode()}", flush=True)
        except Exception as exc:
            print(f"KEEPALIVE V8 CANDLE ERROR -> {exc}", flush=True)
        time.sleep(_INTERVAL_SECONDS)


threading.Thread(
    target=_keep_candle_awake,
    name="v8-candle-keepalive",
    daemon=True,
).start()
