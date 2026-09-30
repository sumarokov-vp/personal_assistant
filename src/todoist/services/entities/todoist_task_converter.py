from datetime import date, datetime

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.task_due import TaskDue
from src.todoist.models.todoist_due import TodoistDue
from src.todoist.models.todoist_task import TodoistTask
from src.todoist.services.entities.todoist_identity import (
    ASSISTANT_LABEL,
    TASK_URL_TEMPLATE,
)
from src.todoist.services.entities.todoist_ref import TodoistRef

ISO_DATE_LENGTH = 10


class TodoistTaskConverter:
    @staticmethod
    def managed(task: TodoistTask, project: str | None) -> ManagedTask:
        return ManagedTask(
            ref=TodoistRef.of(task.id),
            title=task.content,
            description=task.description,
            due=_due(task.due),
            deadline=(
                date.fromisoformat(task.deadline.date[:ISO_DATE_LENGTH])
                if task.deadline is not None
                else None
            ),
            recurring=task.due is not None and task.due.is_recurring,
            by_assistant=ASSISTANT_LABEL in task.labels,
            labels=task.labels,
            project=project,
            parent_ref=TodoistRef.of(task.parent_id) if task.parent_id else None,
            url=TASK_URL_TEMPLATE.format(task_id=task.id),
        )


def _due(due: TodoistDue | None) -> TaskDue | None:
    if due is None:
        return None
    return TaskDue(
        on=date.fromisoformat(due.date[:ISO_DATE_LENGTH]),
        at=datetime.fromisoformat(due.date)
        if len(due.date) > ISO_DATE_LENGTH
        else None,
        text=due.string,
    )
