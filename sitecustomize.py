"""Runtime compatibility tweaks for V8.1.

- Make UptimeRobot HEAD checks behave like GET for the monitored endpoints.
- Expand displayed/API trade history from 20 to 50 trades without touching
  trading strategy, risk, entries, exits, or persistence.
"""

try:
    from functools import wraps
    from fastapi import FastAPI

    # HEAD compatibility for uptime checks.
    _original_call = FastAPI.__call__

    async def _uptime_head_compatible_call(self, scope, receive, send):
        if (
            scope.get("type") == "http"
            and scope.get("method") == "HEAD"
            and scope.get("path") in ("/", "/analyze", "/health")
        ):
            scope = dict(scope)
            scope["method"] = "GET"
        return await _original_call(self, scope, receive, send)

    FastAPI.__call__ = _uptime_head_compatible_call

    # Wrap selected GET endpoints as they are registered by app.py.
    _original_get = FastAPI.get

    def _patched_get(self, path, *args, **kwargs):
        original_decorator = _original_get(self, path, *args, **kwargs)

        def decorator(func):
            if path == "/analyze":
                @wraps(func)
                async def analyze_wrapper(*f_args, **f_kwargs):
                    result = await func(*f_args, **f_kwargs)
                    if isinstance(result, dict):
                        history = func.__globals__.get("trade_history", [])
                        result["trade_history"] = history[:50]
                    return result
                return original_decorator(analyze_wrapper)

            if path == "/":
                @wraps(func)
                async def dashboard_wrapper(*f_args, **f_kwargs):
                    html = await func(*f_args, **f_kwargs)
                    if isinstance(html, str):
                        html = html.replace("Posledních 20 obchodů", "Posledních 50 obchodů")
                        html = html.replace("slice(0,20)", "slice(0,50)")
                    return html
                return original_decorator(dashboard_wrapper)

            return original_decorator(func)

        return decorator

    FastAPI.get = _patched_get

except Exception as exc:
    print("V8.1 RUNTIME PATCH ERROR:", exc)
