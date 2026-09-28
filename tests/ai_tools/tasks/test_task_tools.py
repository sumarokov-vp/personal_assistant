import json
from datetime import date
from zoneinfo import ZoneInfo

from ai_framework import ToolContext

from src.ai_tools.task_add import TaskAddTool
from src.ai_tools.task_add.tool import TaskAddInput
from src.ai_tools.task_close import TaskCloseTool
from src.ai_tools.task_close.tool import TaskCloseInput
from src.ai_tools.task_list import TaskListTool
from src.ai_tools.task_list.tool import TaskListInput
from src.ai_tools.task_update import TaskUpdateTool
from src.ai_tools.task_update.tool import TaskUpdateInput
from src.cases.repos.cases_http_client import CasesHttpClient
from src.cases.services.untrusted_frame.untrusted_case_frame import UntrustedCaseFrame
from tests.ai_tools.tasks.recording_listener import RecordingListener
from tests.cases.conftest import (
    CASE_ID,
    TASK_ID,
    FakeCasesService,
    event_payload,
    task_payload,
)

ALMATY = ZoneInfo("Asia/Almaty")
CONTEXT = ToolContext({})
EVENTS_PATH = f"/api/v1/cases/{CASE_ID}/events"
TASK_PATH = f"/api/v1/tasks/{TASK_ID}"
TASK_EVENT = event_payload(
    id=TASK_ID,
    kind="task",
    summary="Получить справку в консульстве — нужна для РВП",
    task={
        "status": "open",
        "due": "2026-10-20",
        "assignee": "self",
        "external_id": None,
        "closed_at": None,
    },
)


def add_tool(client: CasesHttpClient, listener: RecordingListener) -> TaskAddTool:
    return TaskAddTool(adder=client, timezone=ALMATY, listener=listener)


def test_task_add_posts_task_event_by_contract_and_notifies_listener(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", EVENTS_PATH, 201, TASK_EVENT)
    listener = RecordingListener()

    text = add_tool(client, listener).execute(
        TaskAddInput.model_validate(
            {
                "case_id": CASE_ID,
                "summary": "Получить справку в консульстве — нужна для РВП",
                "assignee": "self",
                "due": "2026-10-20",
                "occurred_at": "2026-09-28T11:00",
            }
        ),
        CONTEXT,
    )

    body = fake_service.last_body()
    assert body == {
        "occurred_at": "2026-09-28T11:00:00+05:00",
        "source": "owner",
        "kind": "task",
        "summary": "Получить справку в консульстве — нужна для РВП",
        "task": {"due": "2026-10-20", "assignee": "self"},
    }
    assert TASK_ID in text
    assert [(case_id, event.id) for case_id, event in listener.recorded] == [
        (CASE_ID, TASK_ID)
    ]


def test_task_add_without_case_goes_to_inbox_case(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", "/api/v1/cases/inbox/events", 201, TASK_EVENT)

    add_tool(client, RecordingListener()).execute(
        TaskAddInput(summary="Позвонить нотариусу", assignee="self"), CONTEXT
    )

    assert fake_service.last().url.path == "/api/v1/cases/inbox/events"


def test_task_add_rejects_unknown_assignee_without_request(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    listener = RecordingListener()

    text = add_tool(client, listener).execute(
        TaskAddInput(case_id=CASE_ID, summary="Позвонить", assignee="nobody"), CONTEXT
    )

    assert "Неизвестный исполнитель" in json.loads(text)["error"]
    assert fake_service.requests == []
    assert listener.recorded == []


def test_task_add_service_error_skips_listener(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", EVENTS_PATH, 404, {"error": "case_not_found"})
    listener = RecordingListener()

    text = add_tool(client, listener).execute(
        TaskAddInput(case_id=CASE_ID, summary="Позвонить", assignee="person:Нотариус"),
        CONTEXT,
    )

    assert "error" in json.loads(text)
    assert listener.recorded == []


def test_task_close_posts_close_and_notifies_listener(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", f"{TASK_PATH}/close", 200, task_payload(status="done"))
    listener = RecordingListener()
    tool = TaskCloseTool(closer=client, timezone=ALMATY, listener=listener)

    text = tool.execute(
        TaskCloseInput(task_id=TASK_ID, status="done", summary="Справку получил"),
        CONTEXT,
    )

    body = fake_service.last_body()
    assert fake_service.last().url.path == f"{TASK_PATH}/close"
    assert body["status"] == "done"
    assert body["source"] == "owner"
    assert body["summary"] == "Справку получил"
    assert "done" in text
    assert [task.status for task in listener.closed] == ["done"]


def test_task_close_service_error_skips_listener(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", f"{TASK_PATH}/close", 404, {"error": "task_not_found"})
    listener = RecordingListener()
    tool = TaskCloseTool(closer=client, timezone=ALMATY, listener=listener)

    text = tool.execute(TaskCloseInput(task_id=TASK_ID, status="cancelled"), CONTEXT)

    assert "error" in json.loads(text)
    assert listener.closed == []


def test_task_update_patches_only_given_fields_and_notifies_listener(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("PATCH", TASK_PATH, 200, task_payload(due="2026-10-15"))
    listener = RecordingListener()
    tool = TaskUpdateTool(updater=client, listener=listener)

    tool.execute(
        TaskUpdateInput(
            task_id=TASK_ID, due=date(2026, 10, 15), summary="Нотариус перенёс приём"
        ),
        CONTEXT,
    )

    assert fake_service.last_body() == {
        "due": "2026-10-15",
        "source": "owner",
        "summary": "Нотариус перенёс приём",
    }
    assert [task.due for task in listener.changed] == [date(2026, 10, 15)]


def test_task_update_rejects_unknown_assignee_without_request(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    tool = TaskUpdateTool(updater=client)

    text = tool.execute(
        TaskUpdateInput(task_id=TASK_ID, assignee="boss", summary="Передаю"), CONTEXT
    )

    assert "Неизвестный исполнитель" in json.loads(text)["error"]
    assert fake_service.requests == []


def test_task_list_shows_only_open_tasks_sorted_by_due(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on(
        "GET",
        "/api/v1/tasks",
        200,
        {
            "items": [
                task_payload(id="t-late", due="2026-11-01", summary="Поздняя"),
                task_payload(id="t-none", due=None, summary="Без срока"),
                task_payload(id="t-done", status="done", summary="Сделанная"),
                task_payload(id="t-soon", due="2026-10-01", summary="Скорая"),
            ]
        },
    )
    tool = TaskListTool(lister=client, frame=UntrustedCaseFrame())

    text = tool.execute(
        TaskListInput(assignee="self", due_before=date(2026, 12, 31)), CONTEXT
    )

    params = fake_service.last().url.params
    assert params["status"] == "open"
    assert params["assignee"] == "self"
    assert params["due_before"] == "2026-12-31"
    task_lines = [line for line in text.splitlines() if line.startswith("t-")]
    assert [line.split(" · ")[0] for line in task_lines] == [
        "t-soon",
        "t-late",
        "t-none",
    ]
    assert task_lines[0] == (
        "t-soon · 01.10.2026 · self · Новая компания (ТОО) · Скорая"
    )
