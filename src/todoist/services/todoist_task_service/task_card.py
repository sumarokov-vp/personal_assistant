from pydantic import BaseModel, Field

from src.todoist.models.todoist_deadline import TodoistDeadline
from src.todoist.models.todoist_due import TodoistDue


class TaskCard(BaseModel):
    id: str
    content: str
    description: str
    due: TodoistDue | None
    deadline: TodoistDeadline | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    parent_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    labels: list[str]
    project: str
    url: str
