import json

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool

from src.ai_tools.find_tasks.tool import FindTasksInput, FindTasksTool
from src.ai_tools.read_task.tool import ReadTaskTool
from src.todoist.services.todoist_task_service.todoist_task_service import (
    TodoistTaskService,
)
from tests.todoist.conftest import WORK_ID, FakeTodoist, task_payload

CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})


def _run(tool: object, model_input: dict) -> dict:
    assert isinstance(tool, BaseTool)
    result = tool.execute(tool.Input.model_validate(model_input), CONTEXT)
    assert isinstance(result, str)
    return json.loads(result)


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
