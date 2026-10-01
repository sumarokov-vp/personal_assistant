from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest

from src.scheduler.errors import (
    CasesUnavailableError,
    LimitReachedError,
    ScheduleCaseNotFoundError,
    ScheduleFinishedError,
    ScheduleInPastError,
    ScheduleNeverFiresError,
    ScheduleNotFoundError,
    SchedulerFailureError,
    SchedulerUnauthorizedError,
    SchedulerUnavailableError,
    SchedulerValidationError,
    TooFrequentError,
)
from src.scheduler.models import NewSchedule, ScheduleQuery
from src.scheduler.repos.scheduler_http_client import SchedulerHttpClient
from tests.scheduler.conftest import (
    API_KEY,
    CASE_ID,
    SCHEDULE_ID,
    Recorder,
    Responder,
    once_payload,
    periodic_payload,
)

type ClientFactory = Callable[[Responder], tuple[SchedulerHttpClient, Recorder]]


def _reply(status: int, body: Any) -> Responder:
    return lambda _request: httpx.Response(status, json=body)


def test_create_once_posts_moment_with_offset(make_client: ClientFactory) -> None:
    client, recorder = make_client(_reply(201, once_payload()))
    moment = datetime(2026, 10, 2, 10, 0, tzinfo=ZoneInfo("Asia/Almaty"))

    schedule = client.create_schedule(
        NewSchedule(
            case_id=CASE_ID,
            instruction="Проверь, ответил ли нотариус",
            at=moment,
            timezone="Asia/Almaty",
        )
    )

    assert recorder.last.method == "POST"
    assert recorder.last.url.path == "/api/v1/schedules"
    assert recorder.last.headers["X-API-Key"] == API_KEY
    assert recorder.last_body() == {
        "case_id": CASE_ID,
        "instruction": "Проверь, ответил ли нотариус",
        "at": "2026-10-02T10:00:00+05:00",
        "timezone": "Asia/Almaty",
    }
    assert schedule.id == SCHEDULE_ID
    assert schedule.kind == "once"


def test_create_periodic_sends_cron_without_at(make_client: ClientFactory) -> None:
    client, recorder = make_client(_reply(201, periodic_payload()))

    schedule = client.create_schedule(
        NewSchedule(
            case_id="inbox",
            instruction="Сверь выписку ABA с реестром",
            cron="0 10 * * 1#1",
            timezone="Asia/Almaty",
        )
    )

    assert recorder.last_body() == {
        "case_id": "inbox",
        "instruction": "Сверь выписку ABA с реестром",
        "cron": "0 10 * * 1#1",
        "timezone": "Asia/Almaty",
    }
    assert len(schedule.upcoming) == 3


def test_list_sends_filters_as_query(make_client: ClientFactory) -> None:
    client, recorder = make_client(_reply(200, {"items": [periodic_payload()]}))

    schedules = client.list_schedules(ScheduleQuery(status="all", case_id=CASE_ID))

    assert recorder.last.method == "GET"
    assert recorder.last.url.path == "/api/v1/schedules"
    assert dict(recorder.last.url.params) == {
        "status": "all",
        "case_id": CASE_ID,
        "limit": "50",
    }
    assert [schedule.cron for schedule in schedules] == ["0 10 * * 1#1"]


def test_cancel_posts_to_cancel_path(make_client: ClientFactory) -> None:
    client, recorder = make_client(_reply(200, once_payload(status="cancelled")))

    schedule = client.cancel_schedule(SCHEDULE_ID)

    assert recorder.last.method == "POST"
    assert recorder.last.url.path == f"/api/v1/schedules/{SCHEDULE_ID}/cancel"
    assert not recorder.last.content
    assert schedule.status == "cancelled"


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (401, {"error": "unauthorized"}, SchedulerUnauthorizedError),
        (404, {"error": "case_not_found"}, ScheduleCaseNotFoundError),
        (503, {"error": "cases_unavailable"}, CasesUnavailableError),
        (422, {"error": "too_frequent", "min_interval_minutes": 15}, TooFrequentError),
        (422, {"error": "limit_reached", "limit": 50}, LimitReachedError),
        (
            422,
            {"error": "validation", "detail": [{"type": "in_past", "msg": "past"}]},
            ScheduleInPastError,
        ),
        (
            422,
            {"error": "validation", "detail": [{"type": "never_fires", "msg": "no"}]},
            ScheduleNeverFiresError,
        ),
        (
            422,
            {"error": "validation", "detail": [{"type": "missing", "msg": "x"}]},
            SchedulerValidationError,
        ),
        (500, {"error": "internal"}, SchedulerFailureError),
    ],
)
def test_create_maps_error_codes(
    make_client: ClientFactory,
    status: int,
    body: dict[str, Any],
    error: type[Exception],
) -> None:
    client, _ = make_client(_reply(status, body))

    with pytest.raises(error):
        client.create_schedule(
            NewSchedule(
                case_id=CASE_ID, instruction="x", cron="* * * * *", timezone="UTC"
            )
        )


def test_too_frequent_carries_service_threshold(make_client: ClientFactory) -> None:
    client, _ = make_client(
        _reply(422, {"error": "too_frequent", "min_interval_minutes": 30})
    )

    with pytest.raises(TooFrequentError, match="30 мин"):
        client.create_schedule(
            NewSchedule(
                case_id=CASE_ID, instruction="x", cron="*/5 * * * *", timezone="UTC"
            )
        )


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (404, {"error": "schedule_not_found"}, ScheduleNotFoundError),
        (409, {"error": "schedule_finished"}, ScheduleFinishedError),
    ],
)
def test_cancel_maps_error_codes(
    make_client: ClientFactory,
    status: int,
    body: dict[str, Any],
    error: type[Exception],
) -> None:
    client, _ = make_client(_reply(status, body))

    with pytest.raises(error, match=SCHEDULE_ID):
        client.cancel_schedule(SCHEDULE_ID)


def test_network_failure_is_unavailable(make_client: ClientFactory) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client, _ = make_client(refuse)

    with pytest.raises(SchedulerUnavailableError):
        client.list_schedules(ScheduleQuery())
