import json
from typing import Any

import httpx

CASE_ID = "0199a1b2-5e4f-7a10-9b2c-3d4e5f607c3d"
CASE_TITLE = "Новая компания (ТОО)"
TODOIST_TASK_ID = "6X7rfFVPjhvv84XG"
PREFIX = "/api/v1"
TASK_FIELDS = ("due", "assignee", "external_id")


class StatefulCasesService:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.tasks: dict[str, dict[str, Any]] = {}
        self.transitions: list[dict[str, Any]] = []
        self.source_refs: set[str] = set()
        self.notes: list[dict[str, Any]] = []

    def add_task(self, task_id: str, **fields: Any) -> dict[str, Any]:
        task = {
            "id": task_id,
            "case": {"id": CASE_ID, "title": CASE_TITLE},
            "summary": "Получить справку в консульстве",
            "occurred_at": "2026-09-28T06:00:00Z",
            "source": "owner",
            "source_ref": None,
            "url": None,
            "status": "open",
            "due": None,
            "assignee": "self",
            "external_id": None,
            "closed_at": None,
            **fields,
        }
        self.tasks[task_id] = task
        return task

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix(PREFIX)
        body = json.loads(request.content) if request.content else {}
        if request.method == "POST" and path.endswith("/events"):
            return self._add_event(body)
        if request.method == "GET" and path == "/tasks":
            return self._list(request.url.params)
        task_id = path.removeprefix("/tasks/").split("/")[0]
        task = self.tasks.get(task_id)
        if task is None:
            return httpx.Response(404, json={"error": "task_not_found"})
        if request.method == "PATCH":
            task.update({name: body[name] for name in TASK_FIELDS if name in body})
            return httpx.Response(200, json=task)
        if path.endswith("/close"):
            return self._transition(task, body, body["status"])
        if path.endswith("/reopen"):
            return self._transition(task, body, "open")
        return httpx.Response(500, text="no fake route")

    def sent(self, method: str, path_end: str) -> list[httpx.Request]:
        return [
            request
            for request in self.requests
            if request.method == method and request.url.path.endswith(path_end)
        ]

    def _add_event(self, body: dict[str, Any]) -> httpx.Response:
        if body["kind"] != "task":
            return self._add_note(body)
        task_id = f"task-{len(self.tasks) + 1}"
        state = body["task"]
        task = self.add_task(
            task_id,
            summary=body["summary"],
            source=body["source"],
            source_ref=body.get("source_ref"),
            url=body.get("url"),
            due=state.get("due"),
            assignee=state["assignee"],
            external_id=state.get("external_id"),
        )
        event = {
            "id": task_id,
            "case_id": CASE_ID,
            "occurred_at": body["occurred_at"],
            "recorded_at": body["occurred_at"],
            "source": body["source"],
            "kind": "task",
            "source_ref": body.get("source_ref"),
            "url": body.get("url"),
            "summary": body["summary"],
            "task": {
                "status": "open",
                "due": task["due"],
                "assignee": task["assignee"],
                "external_id": task["external_id"],
                "closed_at": None,
            },
            "task_event_id": None,
        }
        return httpx.Response(201, json=event)

    def _add_note(self, body: dict[str, Any]) -> httpx.Response:
        self.notes.append(body)
        event = {
            "id": f"note-{len(self.notes)}",
            "case_id": CASE_ID,
            "recorded_at": body["occurred_at"],
            "source_ref": None,
            "url": None,
            "task": None,
            "task_event_id": None,
            **body,
        }
        return httpx.Response(201, json=event)

    def _list(self, params: httpx.QueryParams) -> httpx.Response:
        status = params.get("status", "open")
        items = [
            task
            for task in self.tasks.values()
            if (status == "all" or task["status"] == status)
            and params.get("assignee") in (None, task["assignee"])
            and params.get("external_id") in (None, task["external_id"])
        ]
        return httpx.Response(200, json={"items": items})

    def _transition(
        self, task: dict[str, Any], body: dict[str, Any], status: str
    ) -> httpx.Response:
        source_ref = body.get("source_ref")
        if task["status"] != status and source_ref not in self.source_refs:
            task["status"] = status
            self.transitions.append({"task_id": task["id"], "status": status, **body})
            if source_ref is not None:
                self.source_refs.add(source_ref)
        return httpx.Response(200, json=task)


class StatefulTodoist:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.activities: list[dict[str, Any]] = []
        self.tasks: dict[str, dict[str, Any]] = {}
        self.down = False
        self.closed: list[str] = []

    def activity(self, activity_id: int, event_type: str, **extra: Any) -> None:
        self.activities.append(
            {
                "id": activity_id,
                "object_type": "item",
                "object_id": TODOIST_TASK_ID,
                "event_type": event_type,
                "event_date": f"2026-09-28T07:{len(self.activities):02d}:00Z",
                "extra_data": {"content": "Получить справку", **extra},
            }
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("todoist is down")
        self.requests.append(request)
        path = request.url.path.removeprefix(PREFIX)
        if request.method == "GET" and path == "/activities":
            return httpx.Response(
                200, json={"results": self.activities, "next_cursor": None}
            )
        if request.method == "GET" and path == "/projects":
            return httpx.Response(
                200,
                json={
                    "results": [{"id": "inbox", "name": "Inbox"}],
                    "next_cursor": None,
                },
            )
        if request.method == "GET" and path.startswith("/tasks/"):
            return httpx.Response(200, json=self.tasks[path.removeprefix("/tasks/")])
        if path.endswith("/close"):
            self.closed.append(path.removeprefix("/tasks/").removesuffix("/close"))
            return httpx.Response(204)
        body = json.loads(request.content)
        if path == "/tasks":
            task = todoist_task(TODOIST_TASK_ID, body["content"], body["labels"])
            if body.get("deadline_date"):
                task["deadline"] = {"date": body["deadline_date"]}
            self.tasks[TODOIST_TASK_ID] = task
            return httpx.Response(200, json=task)
        if path.startswith("/tasks/"):
            task = self.tasks[path.removeprefix("/tasks/")]
            task.update(body)
            return httpx.Response(200, json=task)
        return httpx.Response(404, text="not found")

    def sent(self, method: str, path: str) -> list[httpx.Request]:
        return [
            request
            for request in self.requests
            if request.method == method and request.url.path == f"{PREFIX}{path}"
        ]


def todoist_task(task_id: str, content: str, labels: list[str]) -> dict[str, Any]:
    return {
        "id": task_id,
        "content": content,
        "description": "",
        "project_id": "inbox",
        "labels": labels,
        "due": None,
        "deadline": None,
    }
