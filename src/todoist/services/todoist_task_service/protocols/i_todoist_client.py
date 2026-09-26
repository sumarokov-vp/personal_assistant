from typing import Protocol

from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask
from src.todoist.models.todoist_task_update import TodoistTaskUpdate


class ITodoistClient(Protocol):
    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]: ...

    def list_projects(self) -> list[TodoistProject]: ...

    def add_project(self, name: str) -> TodoistProject: ...

    def get_task(self, task_id: str) -> TodoistTask: ...

    def list_subtasks(self, parent_id: str) -> list[TodoistTask]: ...

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

    def list_comments(self, task_id: str) -> list[TodoistComment]: ...

    def add_comment(self, task_id: str, content: str) -> TodoistComment: ...
