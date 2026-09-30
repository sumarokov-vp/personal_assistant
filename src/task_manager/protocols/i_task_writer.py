from datetime import date
from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.new_managed_task import NewManagedTask


class ITaskWriter(Protocol):
    def add_task(self, task: NewManagedTask) -> ManagedTask: ...

    def set_deadline(self, ref: str, deadline: date | None) -> ManagedTask: ...

    def set_due(self, ref: str, due: date) -> ManagedTask: ...
