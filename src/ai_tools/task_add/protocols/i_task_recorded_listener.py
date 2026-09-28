from typing import Protocol

from src.cases.models.case_event import CaseEvent


class ITaskRecordedListener(Protocol):
    def task_recorded(self, case_id: str, task: CaseEvent) -> None: ...
