from collections.abc import Callable
from datetime import UTC, date, datetime

from src.cases.models.case_task import CaseTask
from src.cases.models.new_event import NewEvent
from src.cases.models.new_task import NewTask
from src.cases.models.task_query import TaskQuery
from src.task_mirror.models.todoist_external_id import TodoistExternalId
from src.task_mirror.services.todoist_adoption.protocols.i_adopted_task_recorder import (
    IAdoptedTaskRecorder,
)
from src.task_mirror.services.todoist_adoption.protocols.i_todoist_task_reader import (
    ITodoistTaskReader,
)
from src.todoist.models.todoist_task import TodoistTask

SELF_ASSIGNEE = "self"


class TodoistTaskAdoption:
    def __init__(
        self,
        todoist: ITodoistTaskReader,
        cases: IAdoptedTaskRecorder,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._todoist = todoist
        self._cases = cases
        self._now = now

    def adopt(
        self, todoist_task_id: str, case_id: str, summary: str | None
    ) -> CaseTask:
        external_id = TodoistExternalId.of(todoist_task_id)
        adopted = self._adopted(external_id)
        if adopted is not None:
            return adopted
        todoist_task = self._todoist.get_task(todoist_task_id)
        self._cases.add_event(
            case_id,
            NewEvent(
                occurred_at=self._now(),
                source="todoist",
                kind="task",
                source_ref=external_id,
                url=TodoistExternalId.url(todoist_task.id),
                summary=summary or todoist_task.content,
                task=NewTask(
                    due=_deadline(todoist_task),
                    assignee=SELF_ASSIGNEE,
                    external_id=external_id,
                ),
            ),
        )
        recorded = self._adopted(external_id)
        if recorded is None:
            raise LookupError(f"Задача {external_id} записана, но не найдена")
        return recorded

    def _adopted(self, external_id: str) -> CaseTask | None:
        found = self._cases.list_tasks(
            TaskQuery(status="all", external_id=external_id, limit=1)
        )
        return found[0] if found else None


def _deadline(task: TodoistTask) -> date | None:
    if task.deadline is None:
        return None
    return date.fromisoformat(task.deadline.date)
