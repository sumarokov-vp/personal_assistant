from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.models.todoist_deadline import TodoistDeadline
from src.todoist.models.todoist_due import TodoistDue
from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask
from src.todoist.models.todoist_task_update import TodoistTaskUpdate

INBOX_ID = "inbox"


class InMemoryWiki:
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = dict(files or {})
        self.commits: list[tuple[str, str]] = []

    def read(self, path: str) -> str | None:
        return self.files.get(path)

    def write(self, path: str, content: str, commit_message: str) -> None:
        self.files[path] = content
        self.commits.append((path, commit_message))


class FakeTodoistClient:
    def __init__(self) -> None:
        self.added: list[TodoistTask] = []
        self.added_labels: list[list[str]] = []
        self.comments: list[TodoistComment] = []

    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]:
        return []

    def list_projects(self) -> list[TodoistProject]:
        return [TodoistProject(id=INBOX_ID, name="Inbox")]

    def add_project(self, name: str) -> TodoistProject:
        return TodoistProject(id=f"project-{name}", name=name)

    def get_task(self, task_id: str) -> TodoistTask:
        return next(task for task in self.added if task.id == task_id)

    def list_subtasks(self, parent_id: str) -> list[TodoistTask]:
        return [task for task in self.added if task.parent_id == parent_id]

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
    ) -> TodoistTask:
        task = TodoistTask(
            id=f"task-{len(self.added) + 1}",
            content=content,
            description=description or "",
            project_id=project_id or INBOX_ID,
            parent_id=parent_id,
            labels=labels,
            due=TodoistDue(date=due_string, string=due_string) if due_string else None,
            deadline=TodoistDeadline(date=deadline_date) if deadline_date else None,
        )
        self.added.append(task)
        self.added_labels.append(labels)
        return task

    def update_task(self, task_id: str, update: TodoistTaskUpdate) -> TodoistTask:
        task = self.get_task(task_id)
        return task.model_copy(
            update={"labels": update.labels or task.labels}, deep=True
        )

    def list_comments(self, task_id: str) -> list[TodoistComment]:
        return list(self.comments)

    def add_comment(self, task_id: str, content: str) -> TodoistComment:
        comment = TodoistComment(
            id=f"comment-{len(self.comments) + 1}",
            content=content,
            posted_at="2026-09-26T00:00:00Z",
        )
        self.comments.append(comment)
        return comment
