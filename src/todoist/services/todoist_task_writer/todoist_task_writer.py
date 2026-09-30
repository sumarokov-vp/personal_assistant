from datetime import date

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.new_managed_task import NewManagedTask
from src.task_manager.models.task_manager_identity import TaskManagerIdentity
from src.todoist.models.todoist_task_update import TodoistTaskUpdate
from src.todoist.services.entities.todoist_identity import (
    ASSISTANT_LABEL,
    TODOIST_IDENTITY,
)
from src.todoist.services.entities.todoist_ref import TodoistRef
from src.todoist.services.entities.todoist_task_converter import TodoistTaskConverter
from src.todoist.services.todoist_task_writer.protocols.i_todoist_write_client import (
    ITodoistWriteClient,
)


class TodoistTaskWriter:
    def __init__(self, client: ITodoistWriteClient) -> None:
        self._client = client

    @property
    def identity(self) -> TaskManagerIdentity:
        return TODOIST_IDENTITY

    def add_task(self, task: NewManagedTask) -> ManagedTask:
        created = self._client.add_task(
            content=task.title,
            labels=[ASSISTANT_LABEL],
            description=task.description,
            deadline_date=_iso(task.deadline),
        )
        if task.due is not None:
            created = self._client.update_task(
                created.id, TodoistTaskUpdate(due_date=task.due.isoformat())
            )
        return TodoistTaskConverter.managed(created, project=None)

    def set_deadline(self, ref: str, deadline: date | None) -> ManagedTask:
        updated = self._client.update_task(
            TodoistRef.task_id(ref), TodoistTaskUpdate(deadline_date=_iso(deadline))
        )
        return TodoistTaskConverter.managed(updated, project=None)

    def set_due(self, ref: str, due: date) -> ManagedTask:
        updated = self._client.update_task(
            TodoistRef.task_id(ref), TodoistTaskUpdate(due_date=due.isoformat())
        )
        return TodoistTaskConverter.managed(updated, project=None)

    def close_task(self, ref: str) -> None:
        self._client.close_task(TodoistRef.task_id(ref))


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None
