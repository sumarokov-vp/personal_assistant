from typing import Protocol

from src.todoist.services.todoist_task_service.task_card import TaskCard


class ITaskFinder(Protocol):
    def find(self, query: str, limit: int) -> list[TaskCard]: ...
