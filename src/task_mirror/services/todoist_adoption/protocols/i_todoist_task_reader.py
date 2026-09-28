from typing import Protocol

from src.todoist.models.todoist_task import TodoistTask


class ITodoistTaskReader(Protocol):
    def get_task(self, task_id: str) -> TodoistTask: ...
