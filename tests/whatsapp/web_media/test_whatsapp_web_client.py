import json
from datetime import UTC, datetime

import httpx
import pytest

from src.whatsapp.web_media.models.web_document_request import WebDocumentRequest
from src.whatsapp.web_media.models.web_document_status import WebDocumentStatus
from src.whatsapp.web_media.repos.whatsapp_web_client import WhatsAppWebClient

BASE_URL = "http://host.docker.internal:18790/"
SERVICE_KEY = "web-secret"
DOCUMENT = b"%PDF-1.7 synthetic"
REQUEST = WebDocumentRequest(
    chat_title=None,
    chat_jid="70000000002@s.whatsapp.net",
    file_name="Акт сверки.pdf",
    size=len(DOCUMENT),
    sent_at=datetime(2026, 9, 7, 8, 15, tzinfo=UTC),
)


def client_answering(
    response: httpx.Response,
) -> tuple[WhatsAppWebClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response

    return WhatsAppWebClient(
        BASE_URL, SERVICE_KEY, transport=httpx.MockTransport(handler)
    ), requests


def refusal(status: int, code: str, detail: str = "") -> httpx.Response:
    return httpx.Response(status, json={"error": code, "detail": detail})


def test_document_request_follows_the_contract():
    client, requests = client_answering(
        httpx.Response(200, content=DOCUMENT, headers={"X-Elapsed-Ms": "4120"})
    )

    outcome = client.fetch_document(REQUEST)

    assert outcome.status is WebDocumentStatus.FETCHED
    assert outcome.content == DOCUMENT
    sent = requests[0]
    assert sent.method == "POST"
    assert str(sent.url) == "http://host.docker.internal:18790/v1/documents/fetch"
    assert sent.headers["Authorization"] == f"Bearer {SERVICE_KEY}"
    assert json.loads(sent.content) == {
        "chat_jid": "70000000002@s.whatsapp.net",
        "file_name": "Акт сверки.pdf",
        "size": len(DOCUMENT),
        "sent_at": "2026-09-07T08:15:00Z",
    }


@pytest.mark.parametrize(
    ("response", "words"),
    [
        (
            refusal(409, "not_linked", "привязки нет"),
            "код перепривязки придёт в Telegram",
        ),
        (refusal(504, "reupload_timeout"), "телефон не прислал файл"),
        (refusal(404, "document_not_found"), "документ не нашёлся"),
        (refusal(404, "chat_not_found"), "чат не нашёлся"),
        (refusal(502, "ui_changed", "шаг: вкладка «Документы»"), "изменился интерфейс"),
        (refusal(502, "size_mismatch"), "другого размера"),
        (refusal(401, "unauthorized"), "не принял ключ"),
        (httpx.Response(500, text="Internal Server Error"), "ответил 500"),
    ],
)
def test_refusal_reads_as_words_for_the_owner(response: httpx.Response, words: str):
    client, _ = client_answering(response)

    outcome = client.fetch_document(REQUEST)

    assert outcome.status is WebDocumentStatus.REFUSED
    assert words in outcome.reason


def test_service_detail_is_kept_next_to_the_words():
    client, _ = client_answering(
        refusal(502, "ui_changed", "не нашлась кнопка «Скачать»")
    )

    assert "не нашлась кнопка «Скачать»" in client.fetch_document(REQUEST).reason


def test_unreachable_service_is_not_an_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = WhatsAppWebClient(
        BASE_URL, SERVICE_KEY, transport=httpx.MockTransport(handler)
    )

    assert client.fetch_document(REQUEST).status is WebDocumentStatus.UNREACHABLE
