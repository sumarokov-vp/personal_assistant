from typing import Protocol

from src.task_manager.models.task_manager_identity import TaskManagerIdentity


class ITaskManagerIdentity(Protocol):
    @property
    def identity(self) -> TaskManagerIdentity: ...
