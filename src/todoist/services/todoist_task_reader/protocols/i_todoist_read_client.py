from typing import Protocol

from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask


class ITodoistReadClient(Protocol):
    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]: ...

    def list_projects(self) -> list[TodoistProject]: ...

    def get_task(self, task_id: str) -> TodoistTask: ...

    def list_subtasks(self, parent_id: str) -> list[TodoistTask]: ...

    def list_comments(self, task_id: str) -> list[TodoistComment]: ...
