import json

import pytest

from src.todoist.models.todoist_task_update import TodoistTaskUpdate
from src.todoist.repos.todoist_api_error import TodoistApiError
from src.todoist.repos.todoist_http_client import TodoistHttpClient
from tests.todoist.conftest import FakeTodoist, task_payload


def test_client_closes_but_cannot_reopen_or_delete_tasks() -> None:
    public_methods = {
        name
        for name in dir(TodoistHttpClient)
        if not name.startswith("_") and callable(getattr(TodoistHttpClient, name))
    }
    assert public_methods == {
        "filter_tasks",
        "list_projects",
        "add_project",
        "get_task",
        "list_subtasks",
        "add_task",
        "update_task",
        "close_task",
        "list_comments",
        "add_comment",
        "list_activities",
    }
    forbidden = ("reopen", "delete", "archive", "move")
    assert not [name for name in public_methods if any(w in name for w in forbidden)]


def test_filter_passes_query_as_is_with_bearer_token(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.filter_pages = [
        {"results": [task_payload("1", "Продлить ЭЦП")], "next_cursor": None}
    ]

    tasks = client.filter_tasks("today | overdue & search: ЭЦП", limit=50)

    [request] = fake_todoist.sent_to("GET", "/api/v1/tasks/filter")
    assert request.url.params["query"] == "today | overdue & search: ЭЦП"
    assert request.headers["Authorization"] == "Bearer secret-token"
    assert [task.content for task in tasks] == ["Продлить ЭЦП"]


def test_filter_follows_cursor_until_limit(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.filter_pages = [
        {
            "results": [task_payload("1", "a"), task_payload("2", "b")],
            "next_cursor": "c1",
        },
        {"results": [task_payload("3", "c")], "next_cursor": "c2"},
    ]

    tasks = client.filter_tasks("@pa", limit=3)

    requests = fake_todoist.sent_to("GET", "/api/v1/tasks/filter")
    assert [task.id for task in tasks] == ["1", "2", "3"]
    assert requests[1].url.params["cursor"] == "c1"
    assert requests[1].url.params["limit"] == "1"


def test_add_task_sends_labels_and_due(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    client.add_task("Позвонить", due_string="завтра", due_lang="ru", labels=["pa"])

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks")
    body = json.loads(request.content)
    assert body == {
        "content": "Позвонить",
        "due_string": "завтра",
        "due_lang": "ru",
        "labels": ["pa"],
    }


def test_add_task_with_deadline_and_parent_sends_no_due(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    task = client.add_task(
        "Медсправка",
        labels=["pa"],
        due_lang="ru",
        deadline_date="2026-12-20",
        parent_id="parent-1",
    )

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks")
    assert json.loads(request.content) == {
        "content": "Медсправка",
        "labels": ["pa"],
        "deadline_date": "2026-12-20",
        "parent_id": "parent-1",
    }
    assert task.deadline is not None
    assert task.deadline.date == "2026-12-20"
    assert task.parent_id == "parent-1"
    assert task.due is None


def test_update_task_sends_only_set_fields_and_null_clears_deadline(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload(
        "42", "РВП", deadline={"date": "2026-11-30"}
    )

    client.update_task(
        "42", TodoistTaskUpdate(due_string="no date", deadline_date=None)
    )

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/42")
    assert json.loads(request.content) == {
        "due_string": "no date",
        "deadline_date": None,
    }


def test_add_comment_posts_task_id(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    comment = client.add_comment("42", "vault:rvp/spravka.pdf")

    [request] = fake_todoist.sent_to("POST", "/api/v1/comments")
    assert json.loads(request.content) == {
        "task_id": "42",
        "content": "vault:rvp/spravka.pdf",
    }
    assert comment.content == "vault:rvp/spravka.pdf"


def test_list_comments_follows_cursor(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.comment_pages = [
        {
            "results": [
                {"id": "1", "content": "a", "posted_at": "2026-09-01T00:00:00Z"}
            ],
            "next_cursor": "c1",
        },
        {
            "results": [
                {"id": "2", "content": "b", "posted_at": "2026-09-02T00:00:00Z"}
            ],
            "next_cursor": None,
        },
    ]

    comments = client.list_comments("42")

    requests = fake_todoist.sent_to("GET", "/api/v1/comments")
    assert [comment.id for comment in comments] == ["1", "2"]
    assert requests[0].url.params["task_id"] == "42"
    assert requests[1].url.params["cursor"] == "c1"


def test_api_error_raises(client: TodoistHttpClient, fake_todoist: FakeTodoist) -> None:
    fake_todoist.status_code = 403

    with pytest.raises(TodoistApiError) as error:
        client.list_projects()

    assert error.value.status_code == 403


def test_close_posts_to_close_endpoint_without_body(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    client.close_task("6X7rfFVPjhvv84XG")

    [request] = fake_todoist.requests
    assert request.method == "POST"
    assert request.url.path == "/api/v1/tasks/6X7rfFVPjhvv84XG/close"
    assert request.content == b""


def test_due_date_change_posts_only_due_date(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["1"] = task_payload("1", "Позвонить нотариусу")

    client.update_task("1", TodoistTaskUpdate(due_date="2026-10-02"))

    [request] = fake_todoist.sent_to("POST", "/api/v1/tasks/1")
    assert json.loads(request.content) == {"due_date": "2026-10-02"}
