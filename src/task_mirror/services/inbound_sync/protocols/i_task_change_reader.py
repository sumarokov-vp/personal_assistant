from datetime import datetime
from typing import Protocol

from src.task_manager.models.task_manager_change import TaskManagerChange
from src.task_manager.models.task_manager_identity import TaskManagerIdentity


class ITaskChangeReader(Protocol):
    @property
    def identity(self) -> TaskManagerIdentity: ...

    def changes_since(self, since: datetime) -> list[TaskManagerChange]: ...
