from datetime import date

from pydantic import BaseModel, Field

from src.task_manager.models.task_due import TaskDue


class ManagedTask(BaseModel):
    ref: str
    title: str
    description: str = ""
    due: TaskDue | None = None
    deadline: date | None = None
    recurring: bool = False
    by_assistant: bool = False
    labels: list[str] = Field(default_factory=list)
    project: str | None = None
    parent_ref: str | None = None
    url: str | None = None
