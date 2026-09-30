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


CREATED_TASK_ID = "6X7rfFVPjhvv84XG"
NEW_PROJECT_ID = "6Jf8VQXxpwv56VQ9"


def created_task_payload(body: dict[str, Any]) -> dict[str, Any]:
    due_string = body.get("due_string")
    deadline_date = body.get("deadline_date")
    return task_payload(
        CREATED_TASK_ID,
        body["content"],
        project_id=body.get("project_id", INBOX_ID),
        parent_id=body.get("parent_id"),
        description=body.get("description", ""),
        labels=body["labels"],
        due=None
        if due_string is None
        else {
            "date": "2026-10-01",
            "string": due_string,
            "lang": body.get("due_lang"),
            "is_recurring": False,
            "timezone": None,
        },
        deadline=None if deadline_date is None else {"date": deadline_date},
    )


class FakeTodoist:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.filter_pages: list[dict[str, Any]] = [{"results": [], "next_cursor": None}]
        self.subtask_pages: list[dict[str, Any]] = [
            {"results": [], "next_cursor": None}
        ]
        self.comment_pages: list[dict[str, Any]] = [
            {"results": [], "next_cursor": None}
        ]
        self.tasks: dict[str, dict[str, Any]] = {}
        self.status_code = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status_code != 200:
            return httpx.Response(self.status_code, text="Forbidden")
        path = request.url.path.removeprefix("/api/v1")
        if request.method == "GET":
            return self._get(path)
        if path.endswith("/close"):
            return httpx.Response(204)
        body = json.loads(request.content)
        if path == "/projects":
            return httpx.Response(
                200, json={"id": NEW_PROJECT_ID, "name": body["name"]}
            )
        if path == "/tasks":
            return httpx.Response(200, json=created_task_payload(body))
        if path == "/comments":
            return httpx.Response(
                200,
                json={
                    "id": "c-new",
                    "item_id": body["task_id"],
                    "content": body["content"],
                    "posted_at": "2026-09-26T10:00:00Z",
                },
            )
        if path.startswith("/tasks/"):
            task = {**self.tasks[path.removeprefix("/tasks/")], **body}
            return httpx.Response(200, json=task)
        return httpx.Response(404, text="not found")

    def _get(self, path: str) -> httpx.Response:
        if path == "/projects":
            return httpx.Response(200, json={"results": PROJECTS, "next_cursor": None})
        if path == "/tasks/filter":
            return httpx.Response(200, json=self.filter_pages.pop(0))
        if path == "/tasks":
            return httpx.Response(200, json=self.subtask_pages.pop(0))
        if path == "/comments":
            return httpx.Response(200, json=self.comment_pages.pop(0))
        if path.startswith("/tasks/"):
            return httpx.Response(200, json=self.tasks[path.removeprefix("/tasks/")])
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
