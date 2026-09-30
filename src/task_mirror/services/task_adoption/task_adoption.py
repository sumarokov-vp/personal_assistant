from collections.abc import Callable
from datetime import UTC, datetime

from src.cases.models.case_task import CaseTask
from src.cases.models.new_event import NewEvent
from src.cases.models.new_task import NewTask
from src.cases.models.task_query import TaskQuery
from src.task_mirror.services.entities.task_manager_case_source import (
    TaskManagerCaseSource,
)
from src.task_mirror.services.task_adoption.protocols.i_adoptable_task_reader import (
    IAdoptableTaskReader,
)
from src.task_mirror.services.task_adoption.protocols.i_adopted_task_recorder import (
    IAdoptedTaskRecorder,
)

SELF_ASSIGNEE = "self"


class TaskAdoption:
    def __init__(
        self,
        tasks: IAdoptableTaskReader,
        cases: IAdoptedTaskRecorder,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._tasks = tasks
        self._cases = cases
        self._now = now

    def adopt(self, task_ref: str, case_id: str, summary: str | None) -> CaseTask:
        adopted = self._adopted(task_ref)
        if adopted is not None:
            return adopted
        task = self._tasks.get_task(task_ref)
        self._cases.add_event(
            case_id,
            NewEvent(
                occurred_at=self._now(),
                source=TaskManagerCaseSource.of(self._tasks.identity),
                kind="task",
                source_ref=task.ref,
                url=task.url,
                summary=summary or task.title,
                task=NewTask(
                    due=task.deadline,
                    assignee=SELF_ASSIGNEE,
                    external_id=task.ref,
                ),
            ),
        )
        recorded = self._adopted(task.ref)
        if recorded is None:
            raise LookupError(f"Задача {task.ref} записана, но не найдена")
        return recorded

    def _adopted(self, ref: str) -> CaseTask | None:
        found = self._cases.list_tasks(
            TaskQuery(status="all", external_id=ref, limit=1)
        )
        return found[0] if found else None
