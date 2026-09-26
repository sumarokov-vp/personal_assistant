import json

import pytest
from ai_framework.entities.tool_context import ToolContext
from pydantic import ValidationError

from src.ai_tools.create_task.tool import CreateTaskInput, CreateTaskTool
from src.ai_tools.find_tasks.tool import FindTasksInput, FindTasksTool
from src.todoist.services.todoist_task_service.todoist_task_service import (
    TodoistTaskService,
)
from tests.todoist.conftest import WORK_ID, FakeTodoist, task_payload

CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})


@pytest.mark.parametrize(
    "model_input",
    [
        {"content": "Продлить ЭЦП", "due": "2026-10-01"},
        {"content": "Продлить ЭЦП", "due": "в пятницу", "labels": []},
        {"content": "Продлить ЭЦП", "due": "завтра", "labels": ["work", "urgent"]},
        {"content": "Продлить ЭЦП", "due": "завтра", "project_id": WORK_ID},
    ],
)
def test_create_task_always_sends_pa_label_and_due_to_inbox(
    service: TodoistTaskService, fake_todoist: FakeTodoist, model_input: dict
) -> None:
    tool = CreateTaskTool(service)

    output = json.loads(
        tool.execute(CreateTaskInput.model_validate(model_input), CONTEXT)
    )

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks")
    body = json.loads(request.content)
    assert body["labels"] == ["pa"]
    assert body["due_string"] == model_input["due"]
    assert "project_id" not in body
    assert output["labels"] == ["pa"]
    assert output["project"] == "Inbox"
    assert output["url"] == "https://app.todoist.com/app/task/6X7rfFVPjhvv84XG"


@pytest.mark.parametrize("due", ["", "   "])
def test_create_task_requires_due(due: str) -> None:
    with pytest.raises(ValidationError):
        CreateTaskInput.model_validate({"content": "Продлить ЭЦП", "due": due})


def test_create_task_without_due_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateTaskInput.model_validate({"content": "Продлить ЭЦП"})


def test_find_tasks_passes_filter_as_is_and_names_project(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.filter_pages = [
        {
            "results": [
                task_payload(
                    "42",
                    "Сдать отчёт",
                    project_id=WORK_ID,
                    labels=["pa"],
                    due={
                        "date": "2026-09-26",
                        "string": "today",
                        "is_recurring": False,
                    },
                )
            ],
            "next_cursor": None,
        }
    ]
    tool = FindTasksTool(service)

    output = json.loads(tool.execute(FindTasksInput(query="today | overdue"), CONTEXT))

    [request] = fake_todoist.sent_to("GET", "/api/v1/tasks/filter")
    assert request.url.params["query"] == "today | overdue"
    assert output == {
        "tasks": [
            {
                "id": "42",
                "content": "Сдать отчёт",
                "description": "",
                "due": {"date": "2026-09-26", "string": "today", "is_recurring": False},
                "labels": ["pa"],
                "project": "Работа",
                "url": "https://app.todoist.com/app/task/42",
            }
        ],
        "count": 1,
    }


def test_find_tasks_empty_result_skips_projects(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = json.loads(
        FindTasksTool(service).execute(FindTasksInput(query="@pa"), CONTEXT)
    )

    assert output == {"tasks": [], "count": 0}
    assert fake_todoist.sent_to("GET", "/api/v1/projects") == []
