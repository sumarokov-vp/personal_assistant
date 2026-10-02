from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask

INBOX_ID = "inbox"


class FakeTodoistReadClient:
    def __init__(self, tasks: list[TodoistTask]) -> None:
        self._tasks = tasks

    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]:  # noqa: ARG002
        return self._tasks[:limit]

    def list_projects(self) -> list[TodoistProject]:
        return [TodoistProject(id=INBOX_ID, name="Inbox")]

    def get_task(self, task_id: str) -> TodoistTask:
        return next(task for task in self._tasks if task.id == task_id)

    def list_subtasks(self, parent_id: str) -> list[TodoistTask]:
        return [task for task in self._tasks if task.parent_id == parent_id]

    def list_comments(self, task_id: str) -> list[TodoistComment]:  # noqa: ARG002
        return []
