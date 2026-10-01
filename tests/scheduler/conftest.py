import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from src.scheduler.repos.scheduler_http_client import SchedulerHttpClient

BASE_URL = "http://scheduler.test"
API_KEY = "pa-scheduler-key"
CASE_ID = "0199a1b2-5e4f-7a10-9b2c-3d4e5f607c3d"
SCHEDULE_ID = "0199c000-0000-7000-8000-000000000001"

type Responder = Callable[[httpx.Request], httpx.Response]


def once_payload(**extra: Any) -> dict[str, Any]:
    return {
        "id": SCHEDULE_ID,
        "case_id": CASE_ID,
        "task_event_id": None,
        "kind": "once",
        "run_at": "2026-10-02T05:00:00Z",
        "cron": None,
        "timezone": "Asia/Almaty",
        "instruction": "Проверь, ответил ли нотариус",
        "status": "active",
        "next_run_at": "2026-10-02T05:00:00Z",
        "upcoming": ["2026-10-02T05:00:00Z"],
        "last_run_at": None,
        "created_at": "2026-10-01T06:00:00Z",
        **extra,
    }


def periodic_payload(**extra: Any) -> dict[str, Any]:
    return once_payload(
        kind="periodic",
        run_at=None,
        cron="0 10 * * 1#1",
        instruction="Сверь выписку ABA с реестром",
        next_run_at="2026-10-05T05:00:00Z",
        upcoming=[
            "2026-10-05T05:00:00Z",
            "2026-11-02T05:00:00Z",
            "2026-12-07T05:00:00Z",
        ],
        **extra,
    )


class Recorder:
    def __init__(self, responder: Responder) -> None:
        self.requests: list[httpx.Request] = []
        self._responder = responder

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responder(request)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def last_body(self) -> dict[str, Any]:
        return dict(json.loads(self.last.content))


@pytest.fixture
def make_client() -> Callable[[Responder], tuple[SchedulerHttpClient, Recorder]]:
    def build(responder: Responder) -> tuple[SchedulerHttpClient, Recorder]:
        recorder = Recorder(responder)
        client = SchedulerHttpClient(
            base_url=BASE_URL,
            api_key=API_KEY,
            transport=httpx.MockTransport(recorder),
        )
        return client, recorder

    return build
