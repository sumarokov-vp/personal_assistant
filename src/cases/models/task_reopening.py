from datetime import datetime

from pydantic import BaseModel

from src.cases.models.case_source import CaseSource


class TaskReopening(BaseModel):
    occurred_at: datetime
    source: CaseSource
    source_ref: str | None = None
    summary: str | None = None
