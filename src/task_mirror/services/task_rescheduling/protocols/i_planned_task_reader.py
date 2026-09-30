from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask


class IPlannedTaskReader(Protocol):
    def get_task(self, ref: str) -> ManagedTask: ...
