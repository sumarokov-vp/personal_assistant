from pydantic import BaseModel

from src.todoist.models.todoist_due import TodoistDue


class TaskCard(BaseModel):
    id: str
    content: str
    description: str
    due: TodoistDue | None
    labels: list[str]
    project: str
    url: str
