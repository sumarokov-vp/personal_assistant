from datetime import UTC, date, datetime
from typing import Any

import pytest

from src.task_manager.errors import ForeignTaskRefError
from src.task_manager.models import TaskSearch
from src.todoist.models.todoist_activity import TodoistActivity
from src.todoist.repos.todoist_http_client import TodoistHttpClient
from src.todoist.services.todoist_change_feed import TodoistChangeFeed
from src.todoist.services.todoist_task_reader import (
    TodoistFilterQuery,
    TodoistTaskReader,
)
from src.todoist.services.todoist_task_writer import TodoistTaskWriter
from tests.todoist.conftest import WORK_ID, FakeTodoist, task_payload

SINCE = datetime(2026, 9, 28, tzinfo=UTC)


@pytest.mark.parametrize(
    ("search", "query"),
    [
        (TaskSearch(), "no date | !no date"),
        (TaskSearch(text="ЭЦП"), "search: ЭЦП"),
        (TaskSearch(text="звонок & (срочно)"), "search: звонок \\& \\(срочно\\)"),
        (
            TaskSearch(due_before=date(2026, 10, 3), overdue=True, by_assistant=True),
            "due before: 2026-10-03 & overdue & @pa",
        ),
    ],
)
def test_search_becomes_todoist_filter(search: TaskSearch, query: str) -> None:
    assert TodoistFilterQuery.of(search) == query


def test_reader_gives_port_task_with_ref_dates_and_recurrence(
    client: TodoistHttpClient, fake_todoist: FakeTodoist
) -> None:
    fake_todoist.tasks["42"] = task_payload(
        "42",
        "Оплатить аренду",
        project_id=WORK_ID,
        labels=["pa"],
        due={
            "date": "2026-10-01T10:00:00",
            "string": "каждый месяц",
            "is_recurring": True,
        },
        deadline={"date": "2026-10-05"},
    )

    task = TodoistTaskReader(client).get_task("todoist:42")

    assert task.ref == "todoist:42"
    assert task.due is not None
    assert task.due.on == date(2026, 10, 1)
    assert task.due.at is not None
    assert task.due.at.isoformat() == "2026-10-01T10:00:00"
    assert task.deadline == date(2026, 10, 5)
    assert task.recurring
    assert task.by_assistant
    assert task.project == "Работа"
    assert task.url == "https://app.todoist.com/app/task/42"


def test_writer_refuses_ref_of_another_task_manager(client: TodoistHttpClient) -> None:
    with pytest.raises(ForeignTaskRefError):
        TodoistTaskWriter(client).close_task("ticktick:42")


class ActivityClient:
    def __init__(self, activities: list[dict[str, Any]]) -> None:
        self._activities = activities

    def list_activities(
        self, object_event_types: list[str], since: datetime
    ) -> list[TodoistActivity]:
        return [TodoistActivity.model_validate(item) for item in self._activities]


def _activity(activity_id: int, event_type: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": activity_id,
        "object_type": "item",
        "object_id": "42",
        "event_type": event_type,
        "event_date": f"2026-09-28T07:0{activity_id % 10}:00Z",
        "extra_data": {"content": "Оплатить аренду", **extra},
    }


def test_feed_turns_activities_into_port_changes_in_order() -> None:
    feed = TodoistChangeFeed(
        ActivityClient(
            [
                _activity(3, "updated", due_date="2026-10-04T00:00:00Z", deadline=None),
                _activity(1, "completed"),
                _activity(2, "uncompleted"),
                _activity(4, "updated", description="уточнил"),
                _activity(5, "deleted"),
            ]
        )
    )

    changes = feed.changes_since(SINCE)

    assert [(change.kind, change.deadline, change.due) for change in changes] == [
        ("closed", None, None),
        ("reopened", None, None),
        ("deadline_changed", None, None),
        ("due_changed", None, date(2026, 10, 4)),
        ("deleted", None, None),
    ]
    assert {change.ref for change in changes} == {"todoist:42"}
    assert changes[0].change_ref == "todoist:activity:1"
