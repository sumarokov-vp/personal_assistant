import json

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool

from src.ai_tools.find_tasks.tool import FindTasksTool
from src.ai_tools.read_task.tool import ReadTaskTool
from src.todoist.repos.todoist_http_client import TodoistHttpClient
from src.todoist.services.todoist_task_reader import TodoistTaskReader
from tests.todoist.conftest import WORK_ID, FakeTodoist, task_payload

CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})


def _run(tool: object, model_input: dict) -> dict:
    assert isinstance(tool, BaseTool)
    result = tool.execute(tool.Input.model_validate(model_input), CONTEXT)
    assert isinstance(result, str)
    return json.loads(result)


def test_read_task_returns_subtasks_and_comments(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
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

    output = _run(ReadTaskTool(TodoistTaskReader(client)), {"task_ref": "todoist:42"})

    assert output["task"]["title"] == "Оформить РВП"
    assert output["task"]["by_assistant"] is True
    assert output["task"]["url"] == "https://app.todoist.com/app/task/42"
    assert [subtask["ref"] for subtask in output["subtasks"]] == ["todoist:43"]
    assert output["subtasks"][0]["parent_ref"] == "todoist:42"
    assert output["comments"] == [
        {"text": "Документы/РВП.md", "posted_at": "2026-09-26T10:00:00Z"}
    ]


def test_find_tasks_turns_conditions_into_todoist_filter(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
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

    output = _run(
        FindTasksTool(TodoistTaskReader(client)),
        {
            "text": "отчёт",
            "due_before": "2026-10-01",
            "overdue": True,
            "by_assistant": True,
            "limit": 10,
        },
    )

    [request] = fake_todoist.sent_to("GET", "/api/v1/tasks/filter")
    assert request.url.params["query"] == (
        "search: отчёт & due before: 2026-10-01 & overdue & @pa"
    )
    assert output["count"] == 1
    [task] = output["tasks"]
    assert task["ref"] == "todoist:42"
    assert task["project"] == "Работа"
    assert task["due"]["on"] == "2026-09-26"


def test_find_tasks_empty_result_skips_projects(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    output = _run(FindTasksTool(TodoistTaskReader(client)), {"by_assistant": True})

    assert output == {"tasks": [], "count": 0}
    assert fake_todoist.sent_to("GET", "/api/v1/projects") == []


def test_todoist_failure_is_answered_as_error(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.status_code = 403

    output = _run(FindTasksTool(TodoistTaskReader(client)), {"text": "отчёт"})

    assert "403" in output["error"]
