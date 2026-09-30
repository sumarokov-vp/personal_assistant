from datetime import datetime

from src.cases.models.case_source import CaseSource
from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange
from src.cases.models.task_closure import TaskClosure
from src.cases.models.task_query import TaskQuery
from src.cases.models.task_reopening import TaskReopening
from src.task_manager.models.task_manager_change import TaskManagerChange
from src.task_mirror.services.entities.task_manager_case_source import (
    TaskManagerCaseSource,
)
from src.task_mirror.services.inbound_sync.protocols.i_mirrored_task_book import (
    IMirroredTaskBook,
)
from src.task_mirror.services.inbound_sync.protocols.i_task_change_reader import (
    ITaskChangeReader,
)

SELF_ASSIGNEE = "self"


class InboundSync:
    def __init__(self, tasks: ITaskChangeReader, cases: IMirroredTaskBook) -> None:
        self._tasks = tasks
        self._cases = cases

    def sync(self, since: datetime) -> None:
        source = TaskManagerCaseSource.of(self._tasks.identity)
        known: dict[str, CaseTask | None] = {}
        for change in self._tasks.changes_since(since):
            if change.ref not in known:
                known[change.ref] = self._mirrored_task(change.ref)
            task = known[change.ref]
            if task is not None and task.assignee == SELF_ASSIGNEE:
                known[change.ref] = self._apply(change, task, source)

    def _mirrored_task(self, ref: str) -> CaseTask | None:
        found = self._cases.list_tasks(
            TaskQuery(status="all", external_id=ref, limit=1)
        )
        return found[0] if found else None

    def _apply(
        self, change: TaskManagerChange, task: CaseTask, source: CaseSource
    ) -> CaseTask:
        manager = self._tasks.identity.title
        if change.kind == "closed" and task.status == "open":
            return self._cases.close_task(
                task.id,
                TaskClosure(
                    status="done",
                    occurred_at=change.occurred_at,
                    source=source,
                    source_ref=change.change_ref,
                    summary=f"Закрыта в {manager}",
                ),
            )
        if change.kind == "deleted" and task.status == "open":
            return self._cases.close_task(
                task.id,
                TaskClosure(
                    status="cancelled",
                    occurred_at=change.occurred_at,
                    source=source,
                    source_ref=change.change_ref,
                    summary=f"Удалена в {manager}",
                ),
            )
        if change.kind == "reopened" and task.status == "done":
            return self._cases.reopen_task(
                task.id,
                TaskReopening(
                    occurred_at=change.occurred_at,
                    source=source,
                    source_ref=change.change_ref,
                    summary=f"Снова открыта в {manager}",
                ),
            )
        if (
            change.kind == "deadline_changed"
            and task.status == "open"
            and change.deadline != task.due
        ):
            return self._cases.update_task(
                task.id,
                TaskChange(
                    due=change.deadline,
                    source=source,
                    summary=f"Срок изменён в {manager}",
                ),
            )
        return task
