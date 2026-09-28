from datetime import UTC, date, datetime

import httpx
import pytest

from src.cases.errors.case_not_found_error import CaseNotFoundError
from src.cases.errors.cases_service_unavailable_error import (
    CasesServiceUnavailableError,
)
from src.cases.errors.cases_unauthorized_error import CasesUnauthorizedError
from src.cases.errors.cases_validation_error import CasesValidationError
from src.cases.errors.external_id_taken_error import ExternalIdTakenError
from src.cases.errors.task_not_found_error import TaskNotFoundError
from src.cases.models.case_update import CaseUpdate
from src.cases.models.new_event import NewEvent
from src.cases.models.new_task import NewTask
from src.cases.models.task_change import TaskChange
from src.cases.models.task_closure import TaskClosure
from src.cases.models.task_query import TaskQuery
from src.cases.models.task_reopening import TaskReopening
from src.cases.repos.cases_http_client import CasesHttpClient
from tests.cases.conftest import (
    API_KEY,
    CASE_ID,
    TASK_ID,
    FakeCasesService,
    case_payload,
    event_payload,
    task_payload,
)

CASES = "/api/v1/cases"
TASKS = "/api/v1/tasks"
MOMENT = datetime(2026, 9, 28, 6, 0, tzinfo=UTC)


def test_every_request_carries_api_key(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", CASES, 201, case_payload())
    fake_service.on("GET", CASES, 200, {"items": []})
    fake_service.on("GET", TASKS, 200, {"items": []})

    client.create_case("Новая компания (ТОО)", "Своё ТОО")
    client.find_cases("ТОО", "open", 20)
    client.list_tasks(TaskQuery())

    assert [r.headers["X-API-Key"] for r in fake_service.requests] == [API_KEY] * 3


def test_create_case_posts_title_and_summary(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", CASES, 201, case_payload())

    case = client.create_case("Новая компания (ТОО)", "Своё ТОО")

    assert fake_service.last_body() == {
        "title": "Новая компания (ТОО)",
        "summary": "Своё ТОО",
    }
    assert case.id == CASE_ID


def test_update_case_sends_only_changed_fields(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("PATCH", f"{CASES}/{CASE_ID}", 200, case_payload(status="closed"))

    client.update_case(CASE_ID, CaseUpdate(status="closed"))

    assert fake_service.last_body() == {"status": "closed"}


def test_find_cases_passes_query_status_and_limit(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("GET", CASES, 200, {"items": [case_payload()]})

    cases = client.find_cases("ТОО", "all", 5)

    params = fake_service.last().url.params
    assert (params["q"], params["status"], params["limit"]) == ("ТОО", "all", "5")
    assert [case.title for case in cases] == ["Новая компания (ТОО)"]


def test_read_case_passes_events_limit_and_parses_task_event(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    task_event = event_payload(
        id=TASK_ID,
        kind="task",
        task={
            "status": "open",
            "due": "2026-10-20",
            "assignee": "self",
            "external_id": None,
            "closed_at": None,
        },
    )
    fake_service.on(
        "GET",
        f"{CASES}/{CASE_ID}",
        200,
        {"case": case_payload(), "events": [task_event], "has_earlier": True},
    )

    feed = client.read_case(CASE_ID, 10)

    assert fake_service.last().url.params["events_limit"] == "10"
    assert feed.has_earlier
    assert feed.events[0].task is not None
    assert feed.events[0].task.due == date(2026, 10, 20)


def test_add_task_event_posts_task_fields_by_contract(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on(
        "POST", f"{CASES}/{CASE_ID}/events", 201, event_payload(kind="task")
    )

    addition = client.add_event(
        CASE_ID,
        NewEvent(
            occurred_at=MOMENT,
            source="owner",
            kind="task",
            summary="Получить справку",
            task=NewTask(due=date(2026, 10, 20), assignee="self"),
        ),
    )

    assert fake_service.last_body() == {
        "occurred_at": "2026-09-28T06:00:00Z",
        "source": "owner",
        "kind": "task",
        "summary": "Получить справку",
        "task": {"due": "2026-10-20", "assignee": "self"},
    }
    assert addition.created


def test_repeated_event_is_reported_as_existing(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", f"{CASES}/{CASE_ID}/events", 200, event_payload())

    addition = client.add_event(
        CASE_ID,
        NewEvent(
            occurred_at=MOMENT,
            source="gmail",
            kind="message",
            source_ref="18c2f",
            summary="Письмо нотариуса",
        ),
    )

    assert not addition.created


def test_list_tasks_passes_filters(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("GET", TASKS, 200, {"items": [task_payload()]})

    tasks = client.list_tasks(
        TaskQuery(
            assignee="self",
            due_before=date(2026, 10, 31),
            external_id="todoist:9876543210",
        )
    )

    assert dict(fake_service.last().url.params) == {
        "status": "open",
        "assignee": "self",
        "due_before": "2026-10-31",
        "external_id": "todoist:9876543210",
        "limit": "100",
    }
    assert tasks[0].case.title == "Новая компания (ТОО)"
    assert tasks[0].due == date(2026, 10, 20)


def test_update_task_patches_with_source_and_summary(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("PATCH", f"{TASKS}/{TASK_ID}", 200, task_payload())

    client.update_task(
        TASK_ID,
        TaskChange(
            due=date(2026, 11, 1), source="owner", summary="Консульство закрыто"
        ),
    )

    assert fake_service.last_body() == {
        "due": "2026-11-01",
        "source": "owner",
        "summary": "Консульство закрыто",
    }


def test_close_task_posts_status_and_moment(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on(
        "POST", f"{TASKS}/{TASK_ID}/close", 200, task_payload(status="done")
    )

    task = client.close_task(
        TASK_ID,
        TaskClosure(
            status="done",
            occurred_at=MOMENT,
            source="todoist",
            source_ref="todoist:activity:1",
        ),
    )

    assert fake_service.last_body() == {
        "status": "done",
        "occurred_at": "2026-09-28T06:00:00Z",
        "source": "todoist",
        "source_ref": "todoist:activity:1",
    }
    assert task.status == "done"


def test_reopen_task_posts_moment_and_source(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", f"{TASKS}/{TASK_ID}/reopen", 200, task_payload())

    client.reopen_task(
        TASK_ID,
        TaskReopening(occurred_at=MOMENT, source="owner", summary="Снова нужно"),
    )

    assert fake_service.last_body() == {
        "occurred_at": "2026-09-28T06:00:00Z",
        "source": "owner",
        "summary": "Снова нужно",
    }


def test_missing_case_raises_case_not_found(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("GET", f"{CASES}/{CASE_ID}", 404, {"error": "case_not_found"})

    with pytest.raises(CaseNotFoundError, match="Дело не найдено"):
        client.read_case(CASE_ID, 50)


def test_missing_task_raises_task_not_found(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on(
        "POST", f"{TASKS}/{TASK_ID}/close", 404, {"error": "task_not_found"}
    )

    with pytest.raises(TaskNotFoundError):
        client.close_task(
            TASK_ID, TaskClosure(status="done", occurred_at=MOMENT, source="owner")
        )


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (401, {"error": "unauthorized"}, CasesUnauthorizedError),
        (409, {"error": "external_id_taken"}, ExternalIdTakenError),
        (422, {"error": "validation", "detail": []}, CasesValidationError),
    ],
)
def test_service_errors_map_to_domain_errors(
    client: CasesHttpClient,
    fake_service: FakeCasesService,
    status: int,
    body: dict[str, object],
    error: type[Exception],
) -> None:
    fake_service.on("PATCH", f"{TASKS}/{TASK_ID}", status, body)

    with pytest.raises(error):
        client.update_task(
            TASK_ID, TaskChange(external_id="todoist:1", source="todoist", summary="x")
        )


def test_unreachable_service_raises_unavailable(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.fail("GET", CASES, httpx.ConnectError("connection refused"))

    with pytest.raises(CasesServiceUnavailableError, match="недоступен"):
        client.find_cases(None, "open", 20)
