from starlette.requests import Request
from starlette.responses import JSONResponse

from whatsapp_web.api.protocols.i_relink_trigger import IRelinkTrigger
from whatsapp_web.link.models.relink_start import RelinkStart

DETAIL_BY_START = {
    RelinkStart.STARTED: "Перепривязка запущена: если устройство отвязано, код придёт в Telegram.",
    RelinkStart.RUNNING: "Перепривязка уже идёт: код отправлен или скоро придёт в Telegram.",
    RelinkStart.NO_PHONE: "Номера телефона нет в файле секретов сервиса — перепривязать кодом нельзя.",
}
STATUS_BY_START = {
    RelinkStart.STARTED: 202,
    RelinkStart.RUNNING: 202,
    RelinkStart.NO_PHONE: 409,
}


class LinkEndpoint:
    def __init__(self, relink: IRelinkTrigger) -> None:
        self._relink = relink

    async def handle(self, request: Request) -> JSONResponse:
        start = self._relink.request_attempt(force=True)
        return JSONResponse(
            {"relink": start.value, "detail": DETAIL_BY_START.get(start, "")},
            status_code=STATUS_BY_START.get(start, 202),
        )
