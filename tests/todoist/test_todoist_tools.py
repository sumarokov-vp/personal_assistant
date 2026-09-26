import json

import pytest
from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import ValidationError

from src.ai_tools.add_task_link.tool import AddTaskLinkTool
from src.ai_tools.create_task.tool import CreateTaskInput, CreateTaskTool
from src.ai_tools.find_tasks.tool import FindTasksInput, FindTasksTool
from src.ai_tools.read_task.tool import ReadTaskTool
from src.ai_tools.update_task.tool import UpdateTaskInput, UpdateTaskTool
from src.todoist.services.todoist_task_service.todoist_task_service import (
    TodoistTaskService,
)
from tests.todoist.conftest import NEW_PROJECT_ID, WORK_ID, FakeTodoist, task_payload
from workers.bot.todoist_tools_factory import build_todoist_tools

CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})


def _run(tool: object, model_input: dict) -> dict:
    assert isinstance(tool, BaseTool)
    return json.loads(tool.execute(tool.Input.model_validate(model_input), CONTEXT))


def _created_body(fake_todoist: FakeTodoist) -> dict:
    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks")
    return json.loads(request.content)


def test_create_task_without_due_sends_no_due_string_to_inbox(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(CreateTaskTool(service), {"content": "Оформить РВП"})

    body = _created_body(fake_todoist)
    assert "due_string" not in body
    assert "project_id" not in body
    assert body["labels"] == ["pa"]
    assert output["due"] is None
    assert output["project"] == "Inbox"
    assert output["url"] == "https://app.todoist.com/app/task/6X7rfFVPjhvv84XG"


def test_create_task_sends_deadline_apart_from_due(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(
        CreateTaskTool(service),
        {"content": "Оформить РВП", "due": "в понедельник", "deadline": "2026-12-20"},
    )

    body = _created_body(fake_todoist)
    assert body["due_string"] == "в понедельник"
    assert body["deadline_date"] == "2026-12-20"
    assert output["deadline"] == {"date": "2026-12-20"}


def test_create_task_subtask_goes_under_parent(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(
        CreateTaskTool(service), {"content": "Медсправка", "parent_id": "parent-1"}
    )

    assert _created_body(fake_todoist)["parent_id"] == "parent-1"
    assert output["parent_id"] == "parent-1"


def test_create_task_named_project_resolves_to_its_id(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(
        CreateTaskTool(service), {"content": "Сдать отчёт", "project": "Работа"}
    )

    assert _created_body(fake_todoist)["project_id"] == WORK_ID
    assert output["project"] == "Работа"


def test_create_task_unknown_project_returns_error_without_creating(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(
        CreateTaskTool(service), {"content": "Оформить РВП", "project": "Переезд"}
    )

    assert "Переезд" in output["error"]
    assert fake_todoist.sent_to("POST", "/api/v1/tasks") == []
    assert fake_todoist.sent_to("POST", "/api/v1/projects") == []


def test_create_task_creates_project_only_by_flag(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    _run(
        CreateTaskTool(service),
        {"content": "Оформить РВП", "project": "Переезд", "create_project": True},
    )

    [project_request] = fake_todoist.sent_to("POST", "/api/v1/projects")
    assert json.loads(project_request.content) == {"name": "Переезд"}
    assert _created_body(fake_todoist)["project_id"] == NEW_PROJECT_ID


def test_create_task_adds_named_labels_after_pa(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(
        CreateTaskTool(service), {"content": "Оформить РВП", "labels": ["РВП"]}
    )

    assert _created_body(fake_todoist)["labels"] == ["pa", "РВП"]
    assert output["labels"] == ["pa", "РВП"]


def test_create_task_rejects_deadline_that_is_not_a_date() -> None:
    with pytest.raises(ValidationError):
        CreateTaskInput.model_validate(
            {"content": "Оформить РВП", "deadline": "в ноябре"}
        )


def test_read_task_returns_subtasks_and_link_comments(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload("42", "Оформить РВП", labels=["pa"])
    fake_todoist.subtask_pages = [
        {
            "results": [task_payload("43", "Медсправка", parent_id="42")],
            "next_cursor": None,
        }
    ]
    fake_todoist.comment_pages = [
        {
            "results": [
                {
                    "id": "c1",
                    "item_id": "42",
                    "content": "Документы/РВП.md",
                    "posted_at": "2026-09-26T10:00:00Z",
                }
            ],
            "next_cursor": None,
        }
    ]

    output = _run(ReadTaskTool(service), {"task_id": "42"})

    assert output["task"]["content"] == "Оформить РВП"
    assert output["task"]["url"] == "https://app.todoist.com/app/task/42"
    assert [subtask["id"] for subtask in output["subtasks"]] == ["43"]
    assert output["subtasks"][0]["parent_id"] == "42"
    assert output["comments"] == [
        {"id": "c1", "content": "Документы/РВП.md", "posted_at": "2026-09-26T10:00:00Z"}
    ]


def test_add_task_link_posts_exactly_one_comment(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    output = _run(
        AddTaskLinkTool(service),
        {"task_id": "42", "link": "Документы/РВП.md", "note": "список документов"},
    )

    [request] = fake_todoist.sent_to("POST", "/api/v1/comments")
    assert json.loads(request.content) == {
        "task_id": "42",
        "content": "Документы/РВП.md — список документов",
    }
    assert len([r for r in fake_todoist.requests if r.method == "POST"]) == 1
    assert output["id"] == "c-new"


def test_update_task_clear_deadline_sends_null(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload(
        "42", "Оформить РВП", deadline={"date": "2026-12-20"}
    )

    _run(UpdateTaskTool(service), {"task_id": "42", "clear_deadline": True})

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/42")
    assert json.loads(request.content) == {"deadline_date": None}


def test_update_task_clear_due_sends_no_date(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload("42", "Оформить РВП")

    _run(UpdateTaskTool(service), {"task_id": "42", "clear_due": True})

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/42")
    assert json.loads(request.content)["due_string"] == "no date"


def test_update_task_adds_labels_to_current(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload("42", "Оформить РВП", labels=["работа"])

    _run(UpdateTaskTool(service), {"task_id": "42", "add_labels": ["РВП"]})

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/42")
    assert json.loads(request.content) == {"labels": ["работа", "РВП"]}


@pytest.mark.parametrize(
    "model_input",
    [
        {"task_id": "42"},
        {"task_id": "42", "due": "завтра", "clear_due": True},
        {"task_id": "42", "deadline": "2026-12-20", "clear_deadline": True},
    ],
)
def test_update_task_rejects_empty_or_contradicting_changes(model_input: dict) -> None:
    with pytest.raises(ValidationError):
        UpdateTaskInput.model_validate(model_input)


def test_build_todoist_tools_registers_case_tools() -> None:
    names = [tool.name for tool in build_todoist_tools("secret-token")]

    assert names == [
        "find_tasks",
        "create_task",
        "read_task",
        "add_task_link",
        "update_task",
    ]


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
