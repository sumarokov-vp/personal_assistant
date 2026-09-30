from typing import Protocol

from src.task_manager.models.managed_task_details import ManagedTaskDetails


class ITaskReader(Protocol):
    def read_task(self, ref: str) -> ManagedTaskDetails: ...
