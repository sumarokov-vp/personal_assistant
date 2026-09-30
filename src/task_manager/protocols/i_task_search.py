from typing import Protocol

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.task_search import TaskSearch


class ITaskSearch(Protocol):
    def find_tasks(self, search: TaskSearch) -> list[ManagedTask]: ...
