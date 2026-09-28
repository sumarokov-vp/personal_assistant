from typing import Protocol

from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange
from src.cases.models.task_closure import TaskClosure
from src.cases.models.task_query import TaskQuery
from src.cases.models.task_reopening import TaskReopening


class IMirroredTaskBook(Protocol):
    def list_tasks(self, query: TaskQuery) -> list[CaseTask]: ...

    def update_task(self, task_id: str, change: TaskChange) -> CaseTask: ...

    def close_task(self, task_id: str, closure: TaskClosure) -> CaseTask: ...

    def reopen_task(self, task_id: str, reopening: TaskReopening) -> CaseTask: ...
