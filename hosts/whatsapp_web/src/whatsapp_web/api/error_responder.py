import logging

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError

STATUS_BY_CODE = {
    "chat_not_found": 404,
    "document_not_found": 404,
    "not_linked": 409,
    "ui_changed": 502,
    "size_mismatch": 502,
    "reupload_timeout": 504,
}
BAD_REQUEST_DETAIL = "Запрос не разобран: нужны chat_jid, file_name и size больше нуля. Поля с ошибкой: {fields}."
INTERNAL_DETAIL = "Сервис WhatsApp Web упал на этом запросе, причина — в его логе."

logger = logging.getLogger(__name__)


class ErrorResponder:
    async def fetch_failed(self, request: Request, exc: Exception) -> JSONResponse:
        if not isinstance(exc, DocumentFetchError):
            return await self.internal(request, exc)
        logger.info("request failed: %s", exc.code)
        return self._reply(STATUS_BY_CODE.get(exc.code, 500), exc.code, exc.detail)

    async def bad_request(self, request: Request, exc: Exception) -> JSONResponse:
        fields = "тело запроса"
        if isinstance(exc, ValidationError):
            fields = ", ".join(
                ".".join(str(part) for part in error["loc"]) or "тело запроса"
                for error in exc.errors()
            )
        return self._reply(422, "bad_request", BAD_REQUEST_DETAIL.format(fields=fields))

    async def internal(self, request: Request, exc: Exception) -> JSONResponse:
        logger.error("request crashed: %s", type(exc).__name__)
        return self._reply(500, "internal_error", INTERNAL_DETAIL)

    @staticmethod
    def _reply(status: int, code: str, detail: str) -> JSONResponse:
        return JSONResponse({"error": code, "detail": detail}, status_code=status)
