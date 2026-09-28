from typing import Protocol

from src.cases.models.case_task import CaseTask
from src.cases.models.task_closure import TaskClosure


class ITaskCloser(Protocol):
    def close_task(self, task_id: str, closure: TaskClosure) -> CaseTask: ...
