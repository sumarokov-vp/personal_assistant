from datetime import date
from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.new_managed_task import NewManagedTask
from src.task_manager.models.task_manager_identity import TaskManagerIdentity


class IMirrorTaskWriter(Protocol):
    @property
    def identity(self) -> TaskManagerIdentity: ...

    def add_task(self, task: NewManagedTask) -> ManagedTask: ...

    def set_deadline(self, ref: str, deadline: date | None) -> ManagedTask: ...

    def close_task(self, ref: str) -> None: ...
