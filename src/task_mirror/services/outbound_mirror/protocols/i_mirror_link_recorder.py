from typing import Protocol

from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange


class IMirrorLinkRecorder(Protocol):
    def update_task(self, task_id: str, change: TaskChange) -> CaseTask: ...
