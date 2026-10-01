from typing import Any

import httpx

from src.scheduler.errors.cases_unavailable_error import CasesUnavailableError
from src.scheduler.errors.limit_reached_error import LimitReachedError
from src.scheduler.errors.schedule_case_not_found_error import (
    ScheduleCaseNotFoundError,
)
from src.scheduler.errors.schedule_finished_error import ScheduleFinishedError
from src.scheduler.errors.schedule_in_past_error import ScheduleInPastError
from src.scheduler.errors.schedule_never_fires_error import ScheduleNeverFiresError
from src.scheduler.errors.schedule_not_found_error import ScheduleNotFoundError
from src.scheduler.errors.scheduler_failure_error import SchedulerFailureError
from src.scheduler.errors.scheduler_unauthorized_error import (
    SchedulerUnauthorizedError,
)
from src.scheduler.errors.scheduler_unavailable_error import SchedulerUnavailableError
from src.scheduler.errors.scheduler_validation_error import SchedulerValidationError
from src.scheduler.errors.too_frequent_error import TooFrequentError
from src.scheduler.models.new_schedule import NewSchedule
from src.scheduler.models.schedule import Schedule
from src.scheduler.models.schedule_query import ScheduleQuery

API_PREFIX = "/api/v1"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MIN_INTERVAL_MINUTES = 15
DEFAULT_LIVE_LIMIT = 50
HTTP_CLIENT_ERROR = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422
HTTP_SERVICE_UNAVAILABLE = 503


class SchedulerHttpClient:
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

    def create_schedule(self, schedule: NewSchedule) -> Schedule:
        body = schedule.model_dump(mode="json", exclude_none=True)
        return Schedule.model_validate(
            self._json(
                "POST", f"{API_PREFIX}/schedules", json_body=body, ref=schedule.case_id
            )
        )

    def list_schedules(self, query: ScheduleQuery) -> list[Schedule]:
        params = query.model_dump(mode="json", exclude_none=True)
        page = self._json("GET", f"{API_PREFIX}/schedules", params=params)
        return [Schedule.model_validate(item) for item in page["items"]]

    def cancel_schedule(self, schedule_id: str) -> Schedule:
        return Schedule.model_validate(
            self._json(
                "POST", f"{API_PREFIX}/schedules/{schedule_id}/cancel", ref=schedule_id
            )
        )

    def _json(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        ref: str = "",
    ) -> Any:
        response = self._send(method, path, params, json_body)
        if response.status_code >= HTTP_CLIENT_ERROR:
            raise _error_for(response, ref)
        return response.json()

    def _send(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
    ) -> httpx.Response:
        with httpx.Client(
            timeout=self._timeout, headers=self._headers, transport=self._transport
        ) as client:
            try:
                return client.request(
                    method, f"{self._base_url}{path}", params=params, json=json_body
                )
            except httpx.TransportError as error:
                raise SchedulerUnavailableError(type(error).__name__) from error


def _body(response: httpx.Response) -> dict[str, Any]:
    if not response.headers.get("content-type", "").startswith("application/json"):
        return {}
    body = response.json()
    return body if isinstance(body, dict) else {}


def _validation_type(body: dict[str, Any]) -> str:
    detail = body.get("detail")
    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        return str(detail[0].get("type", ""))
    return ""


def _error_for(response: httpx.Response, ref: str) -> Exception:
    status = response.status_code
    body = _body(response)
    code = str(body.get("error", ""))
    if status == HTTP_UNAUTHORIZED:
        return SchedulerUnauthorizedError()
    if status == HTTP_NOT_FOUND and code == "schedule_not_found":
        return ScheduleNotFoundError(ref)
    if status == HTTP_NOT_FOUND and code == "case_not_found":
        return ScheduleCaseNotFoundError(ref)
    if status == HTTP_CONFLICT and code == "schedule_finished":
        return ScheduleFinishedError(ref)
    if status == HTTP_SERVICE_UNAVAILABLE and code == "cases_unavailable":
        return CasesUnavailableError()
    if status == HTTP_UNPROCESSABLE:
        return _unprocessable(code, body, response.text)
    return SchedulerFailureError(status, response.text)


def _unprocessable(code: str, body: dict[str, Any], text: str) -> Exception:
    if code == "too_frequent":
        return TooFrequentError(
            int(body.get("min_interval_minutes", DEFAULT_MIN_INTERVAL_MINUTES))
        )
    if code == "limit_reached":
        return LimitReachedError(int(body.get("limit", DEFAULT_LIVE_LIMIT)))
    validation_type = _validation_type(body)
    if validation_type == "in_past":
        return ScheduleInPastError()
    if validation_type == "never_fires":
        return ScheduleNeverFiresError()
    return SchedulerValidationError(text)
