from datetime import date
from typing import Literal

from pydantic import BaseModel

TaskStatusFilter = Literal["open", "done", "cancelled", "all"]


class TaskQuery(BaseModel):
    status: TaskStatusFilter = "open"
    assignee: str | None = None
    due_before: date | None = None
    due_after: date | None = None
    case_id: str | None = None
    external_id: str | None = None
    limit: int = 100
