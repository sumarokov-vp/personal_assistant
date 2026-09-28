from datetime import datetime

from pydantic import BaseModel

from src.cases.models.case_source import CaseSource
from src.cases.models.event_kind import EventKind
from src.cases.models.new_task import NewTask


class NewEvent(BaseModel):
    occurred_at: datetime
    source: CaseSource
    kind: EventKind
    source_ref: str | None = None
    url: str | None = None
    summary: str
    task: NewTask | None = None
