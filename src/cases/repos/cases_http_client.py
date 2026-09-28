from typing import Any

import httpx
from pydantic import BaseModel

from src.cases.errors.case_not_found_error import CaseNotFoundError
from src.cases.errors.cases_service_failure_error import CasesServiceFailureError
from src.cases.errors.cases_service_unavailable_error import (
    CasesServiceUnavailableError,
)
from src.cases.errors.cases_unauthorized_error import CasesUnauthorizedError
from src.cases.errors.cases_validation_error import CasesValidationError
from src.cases.errors.external_id_taken_error import ExternalIdTakenError
from src.cases.errors.task_not_found_error import TaskNotFoundError
from src.cases.models.case import Case
from src.cases.models.case_feed import CaseFeed
from src.cases.models.case_task import CaseTask
from src.cases.models.case_update import CaseUpdate
from src.cases.models.event_addition import EventAddition
from src.cases.models.case_event import CaseEvent
from src.cases.models.new_event import NewEvent
from src.cases.models.task_change import TaskChange
from src.cases.models.task_closure import TaskClosure
from src.cases.models.task_query import TaskQuery
from src.cases.models.task_reopening import TaskReopening

API_PREFIX = "/api/v1"
DEFAULT_TIMEOUT_SECONDS = 15.0
HTTP_CREATED = 201
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422
HTTP_CLIENT_ERROR = 400


class CasesHttpClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}
        self._timeout = timeout
        self._transport = transport

    def is_healthy(self) -> bool:
        response = self._send("GET", "/health")
        return response.status_code == httpx.codes.OK

    def create_case(self, title: str, summary: str | None) -> Case:
        body = {"title": title, "summary": summary}
        return Case.model_validate(
            self._json("POST", f"{API_PREFIX}/cases", json_body=_without_none(body))
        )

    def update_case(self, case_id: str, update: CaseUpdate) -> Case:
        return Case.model_validate(
            self._json(
                "PATCH",
                f"{API_PREFIX}/cases/{case_id}",
                json_body=_changes(update),
                missing_id=case_id,
            )
        )

    def find_cases(self, query: str | None, status: str, limit: int) -> list[Case]:
        params = _without_none({"q": query, "status": status, "limit": limit})
        page = self._json("GET", f"{API_PREFIX}/cases", params=params)
        return [Case.model_validate(item) for item in page["items"]]

    def read_case(self, case_id: str, events_limit: int) -> CaseFeed:
        return CaseFeed.model_validate(
            self._json(
                "GET",
                f"{API_PREFIX}/cases/{case_id}",
                params={"events_limit": events_limit},
                missing_id=case_id,
            )
        )

    def add_event(self, case_id: str, event: NewEvent) -> EventAddition:
        response = self._checked(
            "POST",
            f"{API_PREFIX}/cases/{case_id}/events",
            json_body=_payload(event),
            missing_id=case_id,
        )
        return EventAddition(
            event=CaseEvent.model_validate(response.json()),
            created=response.status_code == HTTP_CREATED,
        )

    def list_tasks(self, query: TaskQuery) -> list[CaseTask]:
        page = self._json("GET", f"{API_PREFIX}/tasks", params=_payload(query))
        return [CaseTask.model_validate(item) for item in page["items"]]

    def update_task(self, task_id: str, change: TaskChange) -> CaseTask:
        return CaseTask.model_validate(
            self._json(
                "PATCH",
                f"{API_PREFIX}/tasks/{task_id}",
                json_body=_changes(change),
                missing_id=task_id,
            )
        )

    def close_task(self, task_id: str, closure: TaskClosure) -> CaseTask:
        return CaseTask.model_validate(
            self._json(
                "POST",
                f"{API_PREFIX}/tasks/{task_id}/close",
                json_body=_payload(closure),
                missing_id=task_id,
            )
        )

    def reopen_task(self, task_id: str, reopening: TaskReopening) -> CaseTask:
        return CaseTask.model_validate(
            self._json(
                "POST",
                f"{API_PREFIX}/tasks/{task_id}/reopen",
                json_body=_payload(reopening),
                missing_id=task_id,
            )
        )

    def _json(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        missing_id: str = "",
    ) -> Any:
        return self._checked(method, path, params, json_body, missing_id).json()

    def _checked(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        missing_id: str = "",
    ) -> httpx.Response:
        response = self._send(method, path, params, json_body)
        if response.status_code >= HTTP_CLIENT_ERROR:
            raise _error_for(response, missing_id)
        return response

    def _send(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        with httpx.Client(
            timeout=self._timeout, headers=self._headers, transport=self._transport
        ) as client:
            try:
                return client.request(
                    method, f"{self._base_url}{path}", params=params, json=json_body
                )
            except httpx.TransportError as error:
                raise CasesServiceUnavailableError(type(error).__name__) from error


def _payload(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=True)


def _changes(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_unset=True)


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _error_code(response: httpx.Response) -> str:
    body = response.json() if _is_json(response) else {}
    return str(body.get("error", "")) if isinstance(body, dict) else ""


def _is_json(response: httpx.Response) -> bool:
    return response.headers.get("content-type", "").startswith("application/json")


def _error_for(response: httpx.Response, missing_id: str) -> Exception:
    status = response.status_code
    code = _error_code(response)
    if status == HTTP_UNAUTHORIZED:
        return CasesUnauthorizedError()
    if status == HTTP_NOT_FOUND and code == "case_not_found":
        return CaseNotFoundError(missing_id)
    if status == HTTP_NOT_FOUND and code == "task_not_found":
        return TaskNotFoundError(missing_id)
    if status == HTTP_CONFLICT and code == "external_id_taken":
        return ExternalIdTakenError()
    if status == HTTP_UNPROCESSABLE:
        return CasesValidationError(response.text)
    return CasesServiceFailureError(status, response.text)
