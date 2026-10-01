from datetime import date, datetime

from pydantic import BaseModel

from src.cases.models.case_ref import CaseRef
from src.cases.models.case_source import RecordedSource
from src.cases.models.task_status import TaskStatus


class CaseTask(BaseModel):
    id: str
    case: CaseRef
    summary: str
    occurred_at: datetime
    source: RecordedSource
    source_ref: str | None = None
    url: str | None = None
    status: TaskStatus
    due: date | None = None
    assignee: str
    external_id: str | None = None
    closed_at: datetime | None = None
