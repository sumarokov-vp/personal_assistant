from typing import Protocol

from src.todoist.models.todoist_task import TodoistTask
from src.todoist.models.todoist_task_update import TodoistTaskUpdate


class ITodoistWriteClient(Protocol):
    def add_task(
        self,
        content: str,
        labels: list[str],
        due_string: str | None = None,
        due_lang: str | None = None,
        description: str | None = None,
        deadline_date: str | None = None,
        parent_id: str | None = None,
        project_id: str | None = None,
    ) -> TodoistTask: ...

    def update_task(self, task_id: str, update: TodoistTaskUpdate) -> TodoistTask: ...

    def close_task(self, task_id: str) -> None: ...
