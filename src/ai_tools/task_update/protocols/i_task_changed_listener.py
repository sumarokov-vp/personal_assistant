from typing import Protocol

from src.cases.models.case_task import CaseTask


class ITaskChangedListener(Protocol):
    def task_changed(self, task: CaseTask) -> None: ...
