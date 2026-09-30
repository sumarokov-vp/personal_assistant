from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.task_manager_identity import TaskManagerIdentity


class IAdoptableTaskReader(Protocol):
    @property
    def identity(self) -> TaskManagerIdentity: ...

    def get_task(self, ref: str) -> ManagedTask: ...
