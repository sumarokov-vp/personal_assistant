import json

import pytest

from src.todoist.services.todoist_task_service.todoist_project_not_found_error import (
    TodoistProjectNotFoundError,
)
from src.todoist.services.todoist_task_service.todoist_task_service import (
    TodoistTaskService,
)
from tests.todoist.conftest import NEW_PROJECT_ID, WORK_ID, FakeTodoist, task_payload


def test_unknown_project_without_flag_creates_nothing(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    with pytest.raises(TodoistProjectNotFoundError):
        service.create_assistant_task("Собрать документы", project="РВП")

    assert fake_todoist.sent_to("POST", "/api/v1/tasks") == []
    assert fake_todoist.sent_to("POST", "/api/v1/projects") == []


def test_create_project_only_by_flag(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    card = service.create_assistant_task(
        "Собрать документы", project="РВП", create_project=True
    )

    [project_request] = fake_todoist.sent_to("POST", "/api/v1/projects")
    [task_request] = fake_todoist.sent_to("POST", "/api/v1/tasks")
    assert json.loads(project_request.content) == {"name": "РВП"}
    assert json.loads(task_request.content)["project_id"] == NEW_PROJECT_ID
    assert card.project == NEW_PROJECT_ID


def test_existing_project_matched_by_name_and_named_labels_follow_pa(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    service.create_assistant_task(
        "Сдать отчёт", project="работа", labels=["рвп", "pa"], deadline="2026-11-30"
    )

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks")
    body = json.loads(request.content)
    assert body["project_id"] == WORK_ID
    assert body["labels"] == ["pa", "рвп"]
    assert body["deadline_date"] == "2026-11-30"
    assert "due_string" not in body
    assert "due_lang" not in body


def test_update_keeps_owner_labels_and_never_adds_pa(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload("42", "РВП", labels=["дом"])

    service.update_task("42", due="следующая неделя", labels=["рвп", "pa"])

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/42")
    assert json.loads(request.content) == {
        "due_string": "следующая неделя",
        "due_lang": "ru",
        "labels": ["дом", "рвп"],
    }


def test_update_clears_deadline_with_null(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload(
        "42", "РВП", deadline={"date": "2026-11-30"}
    )

    service.update_task("42", due="no date", clear_deadline=True)

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/42")
    assert json.loads(request.content) == {
        "due_string": "no date",
        "due_lang": "ru",
        "deadline_date": None,
    }


def test_read_task_collects_subtasks_and_comments(
    service: TodoistTaskService, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload("42", "РВП", labels=["pa"])
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
                    "content": "wiki:РВП.md",
                    "posted_at": "2026-09-26T10:00:00Z",
                }
            ],
            "next_cursor": None,
        }
    ]

    details = service.read_task("42")

    [subtask_request] = fake_todoist.sent_to("GET", "/api/v1/tasks")
    assert subtask_request.url.params["parent_id"] == "42"
    assert details.task.content == "РВП"
    assert [(s.id, s.parent_id) for s in details.subtasks] == [("43", "42")]
    assert [c.content for c in details.comments] == ["wiki:РВП.md"]
