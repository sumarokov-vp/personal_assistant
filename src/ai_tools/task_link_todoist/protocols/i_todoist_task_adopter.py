from typing import Protocol

from src.cases.models.case_task import CaseTask


class ITodoistTaskAdopter(Protocol):
    def adopt(
        self, todoist_task_id: str, case_id: str, summary: str | None
    ) -> CaseTask: ...
