import hmac

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

UNAUTHORIZED_DETAIL = "Нет ключа доступа или ключ неверный."


class BearerKeyGuard:
    def __init__(self, app: ASGIApp, api_key: str) -> None:
        self._app = app
        self._expected = f"Bearer {api_key}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        presented = Headers(scope=scope).get("authorization", "").encode()
        if hmac.compare_digest(presented, self._expected):
            await self._app(scope, receive, send)
            return
        response = JSONResponse(
            {"error": "unauthorized", "detail": UNAUTHORIZED_DETAIL},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
