from datetime import datetime

from src.task_manager.models.task_change_kind import TaskChangeKind
from src.task_manager.models.task_manager_change import TaskManagerChange
from src.task_manager.models.task_manager_identity import TaskManagerIdentity
from src.todoist.models.todoist_activity import TodoistActivity
from src.todoist.services.entities.todoist_identity import TODOIST_IDENTITY
from src.todoist.services.entities.todoist_ref import TodoistRef
from src.todoist.services.todoist_change_feed.protocols.i_todoist_activity_client import (
    ITodoistActivityClient,
)
from src.todoist.services.todoist_change_feed.todoist_activity_date import (
    TodoistActivityDate,
)

TRACKED_EVENTS = ["item:completed", "item:uncompleted", "item:updated", "item:deleted"]
ACTIVITY_REF = "todoist:activity:{activity_id}"
DEADLINE_KEY = "deadline"
DUE_KEY = "due_date"
STATE_CHANGES: dict[str, TaskChangeKind] = {
    "completed": "closed",
    "uncompleted": "reopened",
    "deleted": "deleted",
}


class TodoistChangeFeed:
    def __init__(self, client: ITodoistActivityClient) -> None:
        self._client = client

    @property
    def identity(self) -> TaskManagerIdentity:
        return TODOIST_IDENTITY

    def changes_since(self, since: datetime) -> list[TaskManagerChange]:
        activities = sorted(
            self._client.list_activities(TRACKED_EVENTS, since),
            key=lambda activity: activity.event_date,
        )
        return [change for activity in activities for change in _changes(activity)]


def _changes(activity: TodoistActivity) -> list[TaskManagerChange]:
    base = {
        "ref": TodoistRef.of(activity.object_id),
        "occurred_at": activity.event_date,
        "change_ref": (
            ACTIVITY_REF.format(activity_id=activity.id)
            if activity.id is not None
            else None
        ),
    }
    state = STATE_CHANGES.get(activity.event_type)
    if state is not None:
        return [TaskManagerChange.model_validate({**base, "kind": state})]
    if activity.event_type != "updated" or activity.extra_data is None:
        return []
    extra_data = activity.extra_data
    changes: list[TaskManagerChange] = []
    if TodoistActivityDate.touched(extra_data, DEADLINE_KEY):
        changes.append(
            TaskManagerChange.model_validate(
                {
                    **base,
                    "kind": "deadline_changed",
                    "deadline": TodoistActivityDate.new_value(extra_data, DEADLINE_KEY),
                }
            )
        )
    if TodoistActivityDate.touched(extra_data, DUE_KEY):
        changes.append(
            TaskManagerChange.model_validate(
                {
                    **base,
                    "kind": "due_changed",
                    "due": TodoistActivityDate.new_value(extra_data, DUE_KEY),
                }
            )
        )
    return changes
