import json
from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import httpx
import pytest
from ai_framework import ToolContext

from src.ai_tools.schedule_add.tool import ScheduleAddInput, ScheduleAddTool
from src.ai_tools.schedule_cancel.tool import ScheduleCancelInput, ScheduleCancelTool
from src.ai_tools.schedule_list.tool import ScheduleListInput, ScheduleListTool
from src.cases.errors.cases_service_unavailable_error import (
    CasesServiceUnavailableError,
)
from src.cases.models.case import Case
from src.scheduler.repos.scheduler_http_client import SchedulerHttpClient
from tests.scheduler.conftest import (
    CASE_ID,
    SCHEDULE_ID,
    Recorder,
    Responder,
    once_payload,
    periodic_payload,
)

type ClientFactory = Callable[[Responder], tuple[SchedulerHttpClient, Recorder]]

OWNER_TIMEZONE = ZoneInfo("Asia/Almaty")
CONTEXT = ToolContext({})


def _reply(status: int, body: Any) -> Responder:
    return lambda _request: httpx.Response(status, json=body)


def _add(client: SchedulerHttpClient, **fields: Any) -> str:
    tool = ScheduleAddTool(creator=client, timezone=OWNER_TIMEZONE)
    return tool.execute(
        ScheduleAddInput.model_validate(
            {"case_id": CASE_ID, "instruction": "Проверь нотариуса", **fields}
        ),
        CONTEXT,
    )


def test_add_once_without_offset_takes_owner_timezone(
    make_client: ClientFactory,
) -> None:
    client, recorder = make_client(_reply(201, once_payload()))

    answer = _add(client, at="2026-10-02T10:00")

    assert recorder.last_body()["at"] == "2026-10-02T10:00:00+05:00"
    assert recorder.last_body()["timezone"] == "Asia/Almaty"
    assert SCHEDULE_ID in answer
    assert "пт 02.10.2026 10:00" in answer


def test_add_periodic_prints_upcoming_in_owner_timezone(
    make_client: ClientFactory,
) -> None:
    client, recorder = make_client(_reply(201, periodic_payload()))

    answer = _add(client, cron="0 10 * * 1#1")

    assert recorder.last_body() == {
        "case_id": CASE_ID,
        "instruction": "Проверь нотариуса",
        "cron": "0 10 * * 1#1",
        "timezone": "Asia/Almaty",
    }
    for moment in ("пн 05.10.2026 10:00", "пн 02.11.2026 10:00", "пн 07.12.2026 10:00"):
        assert moment in answer


def test_add_naive_moment_follows_explicit_timezone(make_client: ClientFactory) -> None:
    client, recorder = make_client(_reply(201, once_payload(timezone="Europe/Moscow")))

    _add(client, at="2026-10-02T10:00", timezone="Europe/Moscow")

    assert recorder.last_body()["at"] == "2026-10-02T10:00:00+03:00"


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"at": "2026-10-02T10:00", "cron": "0 10 * * 5"},
        {"cron": "0 10 * * 5", "timezone": "Mars/Olympus"},
    ],
)
def test_add_rejects_bad_timing_without_request(
    make_client: ClientFactory, fields: dict[str, Any]
) -> None:
    client, recorder = make_client(_reply(201, once_payload()))

    answer = _add(client, **fields)

    assert "error" in json.loads(answer)
    assert not recorder.requests


@pytest.mark.parametrize(
    ("status", "body", "words"),
    [
        (422, {"error": "too_frequent", "min_interval_minutes": 15}, "15 мин"),
        (422, {"error": "limit_reached", "limit": 50}, "50"),
        (404, {"error": "case_not_found"}, "case_find"),
        (503, {"error": "cases_unavailable"}, "сервис кейсов недоступен"),
    ],
)
def test_add_explains_refusal_to_model(
    make_client: ClientFactory, status: int, body: dict[str, Any], words: str
) -> None:
    client, _ = make_client(_reply(status, body))

    answer = json.loads(_add(client, cron="*/5 * * * *"))

    assert words in answer["error"]


def _case() -> Case:
    return Case(
        id=CASE_ID,
        title="Новая компания (ТОО)",
        status="open",
        created_at=datetime(2026, 9, 20, tzinfo=ZoneInfo("UTC")),
        updated_at=datetime(2026, 9, 20, tzinfo=ZoneInfo("UTC")),
    )


def test_list_prints_lines_with_case_title(make_client: ClientFactory) -> None:
    client, recorder = make_client(
        _reply(200, {"items": [once_payload(), periodic_payload(status="paused")]})
    )
    cases = Mock()
    cases.find_cases.return_value = [_case()]
    tool = ScheduleListTool(lister=client, timezone=OWNER_TIMEZONE, cases=cases)

    answer = tool.execute(ScheduleListInput(case_id=CASE_ID), CONTEXT)

    assert dict(recorder.last.url.params)["status"] == "live"
    assert dict(recorder.last.url.params)["case_id"] == CASE_ID
    lines = answer.splitlines()
    assert lines[1] == (
        f"{SCHEDULE_ID} · пт 02.10.2026 10:00 · Новая компания (ТОО) · "
        "Проверь, ответил ли нотариус"
    )
    assert lines[2].startswith(f"{SCHEDULE_ID} · paused · cron 0 10 * * 1#1")


def test_list_falls_back_to_case_id_when_cases_fail(
    make_client: ClientFactory,
) -> None:
    client, _ = make_client(_reply(200, {"items": [once_payload()]}))
    cases = Mock()
    cases.find_cases.side_effect = CasesServiceUnavailableError("ConnectError")
    tool = ScheduleListTool(lister=client, timezone=OWNER_TIMEZONE, cases=cases)

    answer = tool.execute(ScheduleListInput(), CONTEXT)

    assert f"· {CASE_ID} ·" in answer


def test_cancel_reports_instruction(make_client: ClientFactory) -> None:
    client, recorder = make_client(_reply(200, once_payload(status="cancelled")))
    tool = ScheduleCancelTool(canceller=client)

    answer = tool.execute(ScheduleCancelInput(schedule_id=SCHEDULE_ID), CONTEXT)

    assert recorder.last.url.path == f"/api/v1/schedules/{SCHEDULE_ID}/cancel"
    assert (
        answer == f"Расписание отменено: {SCHEDULE_ID} · Проверь, ответил ли нотариус"
    )


def test_cancel_of_finished_explains(make_client: ClientFactory) -> None:
    client, _ = make_client(_reply(409, {"error": "schedule_finished"}))
    tool = ScheduleCancelTool(canceller=client)

    answer = json.loads(
        tool.execute(ScheduleCancelInput(schedule_id=SCHEDULE_ID), CONTEXT)
    )

    assert "уже выполнено" in answer["error"]
