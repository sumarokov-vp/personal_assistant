from datetime import datetime

from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange
from src.cases.models.task_closure import TaskClosure
from src.cases.models.task_query import TaskQuery
from src.cases.models.task_reopening import TaskReopening
from src.task_mirror.models.todoist_external_id import TodoistExternalId
from src.task_mirror.services.inbound_sync.protocols.i_mirrored_task_book import (
    IMirroredTaskBook,
)
from src.task_mirror.services.inbound_sync.protocols.i_todoist_activity_reader import (
    ITodoistActivityReader,
)
from src.task_mirror.services.inbound_sync.todoist_deadline_change import (
    TodoistDeadlineChange,
)
from src.todoist.models.todoist_activity import TodoistActivity

TRACKED_EVENTS = ["item:completed", "item:uncompleted", "item:updated", "item:deleted"]
SELF_ASSIGNEE = "self"
ACTIVITY_REF = "todoist:activity:{activity_id}"


class TodoistInboundSync:
    def __init__(
        self, todoist: ITodoistActivityReader, cases: IMirroredTaskBook
    ) -> None:
        self._todoist = todoist
        self._cases = cases

    def sync(self, since: datetime) -> None:
        activities = sorted(
            self._todoist.list_activities(TRACKED_EVENTS, since),
            key=lambda activity: activity.event_date,
        )
        known: dict[str, CaseTask | None] = {}
        for activity in activities:
            if activity.object_id not in known:
                known[activity.object_id] = self._mirrored_task(activity.object_id)
            task = known[activity.object_id]
            if task is not None and task.assignee == SELF_ASSIGNEE:
                known[activity.object_id] = self._apply(activity, task)

    def _mirrored_task(self, todoist_task_id: str) -> CaseTask | None:
        found = self._cases.list_tasks(
            TaskQuery(
                status="all",
                external_id=TodoistExternalId.of(todoist_task_id),
                limit=1,
            )
        )
        return found[0] if found else None

    def _apply(self, activity: TodoistActivity, task: CaseTask) -> CaseTask:
        source_ref = _source_ref(activity)
        if activity.event_type == "completed" and task.status == "open":
            return self._cases.close_task(
                task.id,
                TaskClosure(
                    status="done",
                    occurred_at=activity.event_date,
                    source="todoist",
                    source_ref=source_ref,
                    summary="Закрыта в Todoist",
                ),
            )
        if activity.event_type == "deleted" and task.status == "open":
            return self._cases.close_task(
                task.id,
                TaskClosure(
                    status="cancelled",
                    occurred_at=activity.event_date,
                    source="todoist",
                    source_ref=source_ref,
                    summary="Удалена в Todoist",
                ),
            )
        if activity.event_type == "uncompleted" and task.status == "done":
            return self._cases.reopen_task(
                task.id,
                TaskReopening(
                    occurred_at=activity.event_date,
                    source="todoist",
                    source_ref=source_ref,
                    summary="Снова открыта в Todoist",
                ),
            )
        if activity.event_type == "updated" and task.status == "open":
            return self._apply_deadline(activity, task)
        return task

    def _apply_deadline(self, activity: TodoistActivity, task: CaseTask) -> CaseTask:
        extra_data = activity.extra_data
        if extra_data is None or not TodoistDeadlineChange.touched(extra_data):
            return task
        deadline = TodoistDeadlineChange.new_deadline(extra_data)
        if deadline == task.due:
            return task
        return self._cases.update_task(
            task.id,
            TaskChange(
                due=deadline, source="todoist", summary="Срок изменён в Todoist"
            ),
        )


def _source_ref(activity: TodoistActivity) -> str | None:
    if activity.id is None:
        return None
    return ACTIVITY_REF.format(activity_id=activity.id)
