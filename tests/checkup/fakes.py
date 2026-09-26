from src.todoist.models.todoist_due import TodoistDue
from src.todoist.models.todoist_project import TodoistProject
from src.todoist.models.todoist_task import TodoistTask

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

    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]:
        return []

    def list_projects(self) -> list[TodoistProject]:
        return [TodoistProject(id=INBOX_ID, name="Inbox")]

    def add_task(
        self,
        content: str,
        due_string: str,
        due_lang: str,
        labels: list[str],
        description: str | None = None,
    ) -> TodoistTask:
        task = TodoistTask(
            id=f"task-{len(self.added) + 1}",
            content=content,
            description=description or "",
            project_id=INBOX_ID,
            labels=labels,
            due=TodoistDue(date=due_string, string=due_string),
        )
        self.added.append(task)
        self.added_labels.append(labels)
        return task
