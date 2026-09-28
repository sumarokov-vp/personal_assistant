from src.todoist.repos.todoist_error import TodoistError


class TodoistApiError(TodoistError):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Todoist API error {status_code}: {body[:200]}")
        self.status_code = status_code
