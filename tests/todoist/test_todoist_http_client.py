import json

import pytest

from src.todoist.repos.todoist_api_error import TodoistApiError
from src.todoist.repos.todoist_http_client import TodoistHttpClient
from tests.todoist.conftest import FakeTodoist, task_payload


def test_client_has_no_close_update_or_delete() -> None:
    public_methods = {
        name
        for name in dir(TodoistHttpClient)
        if not name.startswith("_") and callable(getattr(TodoistHttpClient, name))
    }
    assert public_methods == {"filter_tasks", "list_projects", "add_task"}


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


def test_api_error_raises(client: TodoistHttpClient, fake_todoist: FakeTodoist) -> None:
    fake_todoist.status_code = 403

    with pytest.raises(TodoistApiError) as error:
        client.list_projects()

    assert error.value.status_code == 403
