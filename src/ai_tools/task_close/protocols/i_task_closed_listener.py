from typing import Protocol

from src.cases.models.case_task import CaseTask


class ITaskClosedListener(Protocol):
    def task_closed(self, task: CaseTask) -> None: ...
