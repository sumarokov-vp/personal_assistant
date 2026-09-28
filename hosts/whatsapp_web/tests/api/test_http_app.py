from datetime import UTC, datetime
from urllib.parse import unquote

import pytest
from starlette.testclient import TestClient

from whatsapp_web.api.http_app import build_http_app
from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.documents.errors.chat_not_found_error import ChatNotFoundError
from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError
from whatsapp_web.documents.errors.document_not_found_error import DocumentNotFoundError
from whatsapp_web.documents.errors.not_linked_error import NotLinkedError
from whatsapp_web.documents.errors.reupload_timeout_error import ReuploadTimeoutError
from whatsapp_web.documents.errors.size_mismatch_error import SizeMismatchError
from whatsapp_web.documents.errors.ui_changed_error import UiChangedError
from whatsapp_web.documents.models.document_request import DocumentRequest
from whatsapp_web.documents.models.fetched_document import FetchedDocument

API_KEY = "test-key"
AUTH = {"Authorization": f"Bearer {API_KEY}"}
BODY = {
    "chat_title": "Выдуманный чат",
    "chat_jid": "70000000000@s.whatsapp.net",
    "file_name": "Выдуманный счёт.pdf",
    "size": 13,
    "sent_at": "2026-09-07T08:15:00Z",
}


class FakeFetcher:
    def __init__(self, error: DocumentFetchError | None = None) -> None:
        self.error = error
        self.requests: list[DocumentRequest] = []

    async def fetch(self, request: DocumentRequest) -> FetchedDocument:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return FetchedDocument(
            file_name=request.file_name,
            content=b"%PDF-1.7 fake",
            content_type="application/pdf",
            elapsed_ms=4120,
        )


class FakeLinkStatus:
    async def current(self) -> LinkState:
        return LinkState(
            linked=True, checked_at=datetime(2026, 9, 28, 11, 20, tzinfo=UTC)
        )


def client(fetcher: FakeFetcher | None = None) -> TestClient:
    app = build_http_app(fetcher or FakeFetcher(), FakeLinkStatus(), API_KEY)
    return TestClient(app, raise_server_exceptions=False)


def test_fetch_returns_file_bytes_and_headers():
    response = client().post("/v1/documents/fetch", json=BODY, headers=AUTH)
    assert response.status_code == 200
    assert response.content == b"%PDF-1.7 fake"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-elapsed-ms"] == "4120"
    encoded = response.headers["x-file-name"]
    assert encoded.startswith("UTF-8''")
    assert unquote(encoded.removeprefix("UTF-8''")) == BODY["file_name"]


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": API_KEY}]
)
def test_fetch_without_valid_key_is_unauthorized(headers: dict[str, str]):
    fetcher = FakeFetcher()
    response = client(fetcher).post("/v1/documents/fetch", json=BODY, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert fetcher.requests == []


def test_health_without_key_is_unauthorized():
    assert client().get("/v1/health").status_code == 401


def test_health_reports_link_state():
    response = client().get("/v1/health", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {"linked": True, "checked_at": "2026-09-28T11:20:00Z"}


@pytest.mark.parametrize("missing", ["chat_jid", "file_name", "size"])
def test_missing_field_is_bad_request(missing: str):
    body = {key: value for key, value in BODY.items() if key != missing}
    response = client().post("/v1/documents/fetch", json=body, headers=AUTH)
    assert response.status_code == 422
    assert response.json()["error"] == "bad_request"
    assert missing in response.json()["detail"]


def test_malformed_json_is_bad_request():
    response = client().post("/v1/documents/fetch", content=b"{not json", headers=AUTH)
    assert response.status_code == 422
    assert response.json()["error"] == "bad_request"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ChatNotFoundError(), 404, "chat_not_found"),
        (DocumentNotFoundError(), 404, "document_not_found"),
        (NotLinkedError(), 409, "not_linked"),
        (UiChangedError("вкладка «Документы»"), 502, "ui_changed"),
        (SizeMismatchError(13, [5]), 502, "size_mismatch"),
        (ReuploadTimeoutError(120), 504, "reupload_timeout"),
    ],
)
def test_fetch_error_maps_to_contract(
    error: DocumentFetchError, status: int, code: str
):
    response = client(FakeFetcher(error)).post(
        "/v1/documents/fetch", json=BODY, headers=AUTH
    )
    assert response.status_code == status
    assert response.json() == {"error": code, "detail": error.detail}


def test_ui_changed_detail_names_the_step():
    response = client(FakeFetcher(UiChangedError("вкладка «Документы»"))).post(
        "/v1/documents/fetch", json=BODY, headers=AUTH
    )
    assert "вкладка «Документы»" in response.json()["detail"]
