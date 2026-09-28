from datetime import datetime

from pydantic import BaseModel

from src.cases.models.case_status import CaseStatus


class Case(BaseModel):
    id: str
    title: str
    summary: str | None = None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    last_event_at: datetime | None = None
