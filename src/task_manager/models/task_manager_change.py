from datetime import date, datetime

from pydantic import BaseModel

from src.task_manager.models.task_change_kind import TaskChangeKind


class TaskManagerChange(BaseModel):
    ref: str
    kind: TaskChangeKind
    occurred_at: datetime
    change_ref: str | None = None
    deadline: date | None = None
    due: date | None = None
