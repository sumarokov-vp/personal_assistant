from pydantic import BaseModel, Field

from src.todoist.models.todoist_deadline import TodoistDeadline
from src.todoist.models.todoist_due import TodoistDue


class TodoistTask(BaseModel):
    id: str
    content: str
    description: str = ""
    project_id: str
    parent_id: str | None = None
    labels: list[str] = Field(default_factory=list)
    due: TodoistDue | None = None
    deadline: TodoistDeadline | None = None
