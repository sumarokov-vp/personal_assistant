from datetime import date
from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.task_manager_identity import TaskManagerIdentity


class IPlannedTaskWriter(Protocol):
    @property
    def identity(self) -> TaskManagerIdentity: ...

    def set_due(self, ref: str, due: date) -> ManagedTask: ...
