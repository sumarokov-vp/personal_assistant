from typing import Protocol

from src.todoist.services.todoist_task_service.task_details import TaskDetails


class ITaskReader(Protocol):
    def read_task(self, task_id: str) -> TaskDetails: ...
