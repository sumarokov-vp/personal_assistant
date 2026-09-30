from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.managed_task_details import ManagedTaskDetails


class ITaskReader(Protocol):
    def get_task(self, ref: str) -> ManagedTask: ...

    def read_task(self, ref: str) -> ManagedTaskDetails: ...
