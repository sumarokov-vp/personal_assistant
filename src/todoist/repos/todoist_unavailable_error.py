from src.todoist.repos.todoist_error import TodoistError


class TodoistUnavailableError(TodoistError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Todoist недоступен: {reason}")
