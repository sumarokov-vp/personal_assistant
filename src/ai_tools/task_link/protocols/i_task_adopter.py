from typing import Protocol

from src.cases.models.case_task import CaseTask


class ITaskAdopter(Protocol):
    def adopt(self, task_ref: str, case_id: str, summary: str | None) -> CaseTask: ...
