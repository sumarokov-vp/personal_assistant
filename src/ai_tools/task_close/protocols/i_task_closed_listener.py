from typing import Protocol

from src.cases.models.case_task import CaseTask
from src.cases.models.task_closure import TaskClosure


class ITaskClosedListener(Protocol):
    def task_closed(self, task: CaseTask, closure: TaskClosure) -> None: ...
