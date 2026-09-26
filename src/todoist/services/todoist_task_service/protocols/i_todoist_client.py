from typing import Protocol

from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask


class ITodoistClient(Protocol):
    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]: ...

    def list_projects(self) -> list[TodoistProject]: ...

    def add_task(
        self,
        content: str,
        due_string: str,
        due_lang: str,
        labels: list[str],
        description: str | None = None,
    ) -> TodoistTask: ...
