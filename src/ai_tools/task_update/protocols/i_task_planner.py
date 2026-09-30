from datetime import date
from typing import Protocol

from src.cases.models.case_source import CaseSource
from src.cases.models.case_task import CaseTask


class ITaskPlanner(Protocol):
    def reschedule(
        self, task: CaseTask, planned: date, reason: str, source: CaseSource
    ) -> None: ...
