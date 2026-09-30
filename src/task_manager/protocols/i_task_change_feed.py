from datetime import datetime
from typing import Protocol

from src.task_manager.models.task_manager_change import TaskManagerChange


class ITaskChangeFeed(Protocol):
    def changes_since(self, since: datetime) -> list[TaskManagerChange]: ...
