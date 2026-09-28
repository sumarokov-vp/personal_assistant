import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from src.cases.repos.cases_http_client import CasesHttpClient

BASE_URL = "http://cases.test"
API_KEY = "pa-secret-key"
CASE_ID = "0199a1b2-5e4f-7a10-9b2c-3d4e5f607c3d"
TASK_ID = "0199a1c0-11aa-7b22-8c33-4d5e6f708192"

type Responder = Callable[[httpx.Request], httpx.Response]


def case_payload(**extra: Any) -> dict[str, Any]:
    return {
        "id": CASE_ID,
        "title": "Новая компания (ТОО)",
        "summary": "Своё ТОО после ухода от партнёров",
        "status": "open",
        "created_at": "2026-09-20T10:00:00Z",
        "updated_at": "2026-09-28T06:00:00Z",
        "last_event_at": "2026-09-28T06:00:00Z",
        **extra,
    }


def task_payload(**extra: Any) -> dict[str, Any]:
    return {
        "id": TASK_ID,
        "case": {"id": CASE_ID, "title": "Новая компания (ТОО)"},
        "summary": "Получить справку в консульстве — нужна для РВП бизнес-мигранта",
        "occurred_at": "2026-09-28T06:00:00Z",
        "source": "owner",
        "source_ref": None,
        "url": None,
        "status": "open",
        "due": "2026-10-20",
        "assignee": "self",
        "external_id": "todoist:9876543210",
        "closed_at": None,
        **extra,
    }


def event_payload(**extra: Any) -> dict[str, Any]:
    return {
        "id": "0199a1d0-0000-7000-8000-000000000001",
        "case_id": CASE_ID,
        "occurred_at": "2026-09-28T06:00:00Z",
        "recorded_at": "2026-09-28T06:00:01Z",
        "source": "owner",
        "kind": "note",
        "source_ref": None,
        "url": None,
        "summary": "Справку из поликлиники забрал",
        **extra,
    }


class FakeCasesService:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.responders: dict[tuple[str, str], Responder] = {}

    def on(self, method: str, path: str, status: int, body: Any) -> None:
        self.responders[(method, path)] = lambda _request: httpx.Response(
            status, json=body
        )

    def fail(self, method: str, path: str, error: Exception) -> None:
        def raise_error(_request: httpx.Request) -> httpx.Response:
            raise error

        self.responders[(method, path)] = raise_error

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        responder = self.responders.get((request.method, request.url.path))
        if responder is None:
            return httpx.Response(500, text="no fake route")
        return responder(request)

    def last(self) -> httpx.Request:
        return self.requests[-1]

    def last_body(self) -> Any:
        return json.loads(self.last().content)


@pytest.fixture
def fake_service() -> FakeCasesService:
    return FakeCasesService()


@pytest.fixture
def client(fake_service: FakeCasesService) -> CasesHttpClient:
    return CasesHttpClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        transport=httpx.MockTransport(fake_service.handle),
    )
