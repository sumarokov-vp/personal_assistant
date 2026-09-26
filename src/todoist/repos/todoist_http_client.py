from typing import Any

import httpx

from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask
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
        projects: list[TodoistProject] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"limit": MAX_PAGE_SIZE}
            if cursor:
                params["cursor"] = cursor
            page = self._request_json("GET", "/projects", params=params)
            projects.extend(
                TodoistProject.model_validate(item) for item in page["results"]
            )
            cursor = page.get("next_cursor")
            if not cursor:
                return projects

    def add_task(
        self,
        content: str,
        due_string: str,
        due_lang: str,
        labels: list[str],
        description: str | None = None,
    ) -> TodoistTask:
        body: dict[str, Any] = {
            "content": content,
            "due_string": due_string,
            "due_lang": due_lang,
            "labels": labels,
        }
        if description:
            body["description"] = description
        return TodoistTask.model_validate(
            self._request_json("POST", "/tasks", json_body=body)
        )

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
