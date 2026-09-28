import httpx

from src.whatsapp.web_media.models.web_document_outcome import WebDocumentOutcome
from src.whatsapp.web_media.models.web_document_request import WebDocumentRequest
from src.whatsapp.web_media.models.web_document_status import WebDocumentStatus
from src.whatsapp.web_media.services.refusal_wording.refusal_wording import (
    refusal_wording,
)

DOCUMENT_FETCH_PATH = "/v1/documents/fetch"
DEFAULT_TIMEOUT_SECONDS = 150.0
OK = 200


class WhatsAppWebClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + DOCUMENT_FETCH_PATH
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = timeout_seconds
        self._transport = transport

    def fetch_document(self, request: WebDocumentRequest) -> WebDocumentOutcome:
        with httpx.Client(
            timeout=self._timeout, headers=self._headers, transport=self._transport
        ) as client:
            try:
                response = client.post(
                    self._url, json=request.model_dump(mode="json", exclude_none=True)
                )
            except httpx.TransportError:
                return WebDocumentOutcome(status=WebDocumentStatus.UNREACHABLE)
        if response.status_code == OK:
            return WebDocumentOutcome(
                status=WebDocumentStatus.FETCHED, content=response.content
            )
        code, detail = _error_fields(response)
        return WebDocumentOutcome(
            status=WebDocumentStatus.REFUSED,
            reason=refusal_wording(response.status_code, code, detail),
        )


def _error_fields(response: httpx.Response) -> tuple[str, str]:
    if not response.headers.get("content-type", "").startswith("application/json"):
        return "", ""
    body = response.json()
    if not isinstance(body, dict):
        return "", ""
    return str(body.get("error") or ""), str(body.get("detail") or "")
