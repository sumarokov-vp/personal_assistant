import json
from typing import Any

import httpx
import pytest

from src.todoist.repos.todoist_http_client import TodoistHttpClient
from src.todoist.services.todoist_task_service.todoist_task_service import (
    TodoistTaskService,
)

INBOX_ID = "6X7rM8997g3RQmvh"
WORK_ID = "6Jf8VQXxpwv56VQ7"

PROJECTS = [
    {"id": INBOX_ID, "name": "Inbox", "inbox_project": True},
    {"id": WORK_ID, "name": "Работа", "inbox_project": False},
]


def task_payload(
    task_id: str, content: str, project_id: str = INBOX_ID, **extra: Any
) -> dict[str, Any]:
    return {
        "id": task_id,
        "content": content,
        "description": "",
        "project_id": project_id,
        "labels": [],
        "due": None,
        "priority": 1,
        "checked": False,
        **extra,
    }


class FakeTodoist:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.filter_pages: list[dict[str, Any]] = [{"results": [], "next_cursor": None}]
        self.status_code = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status_code != 200:
            return httpx.Response(self.status_code, text="Forbidden")
        if request.method == "GET" and request.url.path == "/api/v1/projects":
            return httpx.Response(200, json={"results": PROJECTS, "next_cursor": None})
        if request.method == "GET" and request.url.path == "/api/v1/tasks/filter":
            return httpx.Response(200, json=self.filter_pages.pop(0))
        if request.method == "POST" and request.url.path == "/api/v1/tasks":
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json=task_payload(
                    "6X7rfFVPjhvv84XG",
                    body["content"],
                    description=body.get("description", ""),
                    labels=body["labels"],
                    due={
                        "date": "2026-10-01",
                        "string": body["due_string"],
                        "lang": body["due_lang"],
                        "is_recurring": False,
                        "timezone": None,
                    },
                ),
            )
        return httpx.Response(404, text="not found")

    def sent_to(self, method: str, path: str) -> list[httpx.Request]:
        return [
            request
            for request in self.requests
            if request.method == method and request.url.path == path
        ]


@pytest.fixture
def fake_todoist() -> FakeTodoist:
    return FakeTodoist()


@pytest.fixture
def client(fake_todoist: FakeTodoist) -> TodoistHttpClient:
    return TodoistHttpClient(
        "secret-token", transport=httpx.MockTransport(fake_todoist.handler)
    )


@pytest.fixture
def service(client: TodoistHttpClient) -> TodoistTaskService:
    return TodoistTaskService(client)
