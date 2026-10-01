from datetime import datetime

from pydantic import BaseModel

from src.cases.models.case_source import RecordedSource
from src.cases.models.event_kind import EventKind
from src.cases.models.task_state import TaskState


class CaseEvent(BaseModel):
    id: str
    case_id: str | None = None
    occurred_at: datetime
    recorded_at: datetime | None = None
    source: RecordedSource
    kind: EventKind
    source_ref: str | None = None
    url: str | None = None
    summary: str
    task: TaskState | None = None
    task_event_id: str | None = None
