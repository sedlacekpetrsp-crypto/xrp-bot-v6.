"""Compatibility patch for uptime monitors.

UptimeRobot checks the service root with HTTP HEAD. FastAPI/Starlette does not
implicitly map HEAD to the existing GET / route in this app, so the monitor
received 405 even while the bot was healthy. This patch treats HEAD / exactly
like GET / at the ASGI layer. Trading logic is untouched.
"""

try:
    from starlette.applications import Starlette

    _original_call = Starlette.__call__

    async def _uptime_head_compatible_call(self, scope, receive, send):
        if (
            scope.get("type") == "http"
            and scope.get("method") == "HEAD"
            and scope.get("path") == "/"
        ):
            scope = dict(scope)
            scope["method"] = "GET"
        return await _original_call(self, scope, receive, send)

    Starlette.__call__ = _uptime_head_compatible_call
except Exception as exc:
    print("UPTIME HEAD PATCH ERROR:", exc)
