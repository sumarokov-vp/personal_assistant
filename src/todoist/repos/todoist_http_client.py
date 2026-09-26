from typing import Any

import httpx

from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask
from src.todoist.models.todoist_task_update import TodoistTaskUpdate
from src.todoist.repos.todoist_api_error import TodoistApiError

TODOIST_BASE_URL = "https://api.todoist.com/api/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_PAGE_SIZE = 200


class TodoistHttpClient:
    def __init__(
        self,
        token: str,
        base_url: str = TODOIST_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._headers = {"Authorization": f"Bearer {token}"}
        self._transport = transport

    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]:
        tasks: list[TodoistTask] = []
        cursor: str | None = None
        while len(tasks) < limit:
            params: dict[str, Any] = {
                "query": query,
                "limit": min(limit - len(tasks), MAX_PAGE_SIZE),
            }
            if cursor:
                params["cursor"] = cursor
            page = self._request_json("GET", "/tasks/filter", params=params)
            tasks.extend(TodoistTask.model_validate(item) for item in page["results"])
            cursor = page.get("next_cursor")
            if not cursor:
                break
        return tasks[:limit]

    def list_projects(self) -> list[TodoistProject]:
        return [
            TodoistProject.model_validate(item)
            for item in self._all_pages("/projects", {})
        ]

    def add_project(self, name: str) -> TodoistProject:
        return TodoistProject.model_validate(
            self._request_json("POST", "/projects", json_body={"name": name})
        )

    def get_task(self, task_id: str) -> TodoistTask:
        return TodoistTask.model_validate(
            self._request_json("GET", f"/tasks/{task_id}")
        )

    def list_subtasks(self, parent_id: str) -> list[TodoistTask]:
        return [
            TodoistTask.model_validate(item)
            for item in self._all_pages("/tasks", {"parent_id": parent_id})
        ]

    def add_task(
        self,
        content: str,
        labels: list[str],
        due_string: str | None = None,
        due_lang: str | None = None,
        description: str | None = None,
        deadline_date: str | None = None,
        parent_id: str | None = None,
        project_id: str | None = None,
    ) -> TodoistTask:
        optional = {
            "description": description,
            "due_string": due_string,
            "due_lang": due_lang if due_string else None,
            "deadline_date": deadline_date,
            "parent_id": parent_id,
            "project_id": project_id,
        }
        body: dict[str, Any] = {"content": content, "labels": labels}
        body.update({key: value for key, value in optional.items() if value})
        return TodoistTask.model_validate(
            self._request_json("POST", "/tasks", json_body=body)
        )

    def update_task(self, task_id: str, update: TodoistTaskUpdate) -> TodoistTask:
        return TodoistTask.model_validate(
            self._request_json(
                "POST",
                f"/tasks/{task_id}",
                json_body=update.model_dump(exclude_unset=True),
            )
        )

    def list_comments(self, task_id: str) -> list[TodoistComment]:
        return [
            TodoistComment.model_validate(item)
            for item in self._all_pages("/comments", {"task_id": task_id})
        ]

    def add_comment(self, task_id: str, content: str) -> TodoistComment:
        return TodoistComment.model_validate(
            self._request_json(
                "POST",
                "/comments",
                json_body={"task_id": task_id, "content": content},
            )
        )

    def _all_pages(self, path: str, filters: dict[str, Any]) -> list[Any]:
        items: list[Any] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {**filters, "limit": MAX_PAGE_SIZE}
            if cursor:
                params["cursor"] = cursor
            page = self._request_json("GET", path, params=params)
            items.extend(page["results"])
            cursor = page.get("next_cursor")
            if not cursor:
                return items

    def _request_json(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        with httpx.Client(
            timeout=DEFAULT_TIMEOUT_SECONDS,
            headers=self._headers,
            transport=self._transport,
        ) as client:
            response = client.request(
                method, f"{self._base_url}{path}", params=params, json=json_body
            )
        if response.status_code >= 400:
            raise TodoistApiError(response.status_code, response.text)
        return response.json()
