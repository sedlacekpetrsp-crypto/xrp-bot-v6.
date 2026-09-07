"""Runtime compatibility tweaks for V8.1.

- Register explicit HEAD routes for uptime checks on /, /analyze and /health.
- Expand displayed/API trade history from 20 to 50 trades.
- Trading strategy, risk, entries, exits and persistence are untouched.
"""

try:
    from functools import wraps
    from fastapi import FastAPI

    _original_get = FastAPI.get

    def _patched_get(self, path, *args, **kwargs):
        original_decorator = _original_get(self, path, *args, **kwargs)

        def decorator(func):
            endpoint = func

            if path == "/analyze":
                @wraps(func)
                async def analyze_wrapper(*f_args, **f_kwargs):
                    result = await func(*f_args, **f_kwargs)
                    if isinstance(result, dict):
                        history = func.__globals__.get("trade_history", [])
                        result["trade_history"] = history[:50]
                    return result
                endpoint = analyze_wrapper

            elif path == "/":
                @wraps(func)
                async def dashboard_wrapper(*f_args, **f_kwargs):
                    html = await func(*f_args, **f_kwargs)
                    if isinstance(html, str):
                        html = html.replace("Posledních 20 obchodů", "Posledních 50 obchodů")
                        html = html.replace("slice(0,20)", "slice(0,50)")
                    return html
                endpoint = dashboard_wrapper

            registered = original_decorator(endpoint)

            # Explicit HEAD route. This is what UptimeRobot uses.
            if path in ("/", "/analyze", "/health"):
                async def head_ok():
                    return None
                self.add_api_route(
                    path,
                    head_ok,
                    methods=["HEAD"],
                    include_in_schema=False,
                    status_code=200,
                )

            return registered

        return decorator

    FastAPI.get = _patched_get

except Exception as exc:
    print("V8.1 RUNTIME PATCH ERROR:", exc)
