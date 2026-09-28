from starlette.requests import Request
from starlette.responses import JSONResponse

from whatsapp_web.api.protocols.i_link_status import ILinkStatus


class HealthEndpoint:
    def __init__(self, link_status: ILinkStatus) -> None:
        self._link_status = link_status

    async def handle(self, request: Request) -> JSONResponse:
        state = await self._link_status.current()
        checked_at = state.checked_at.isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
        return JSONResponse({"linked": state.linked, "checked_at": checked_at})
