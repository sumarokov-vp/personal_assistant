from datetime import date, datetime

from pydantic import BaseModel

from src.cases.models.task_status import TaskStatus


class TaskState(BaseModel):
    status: TaskStatus
    due: date | None = None
    assignee: str
    external_id: str | None = None
    closed_at: datetime | None = None
