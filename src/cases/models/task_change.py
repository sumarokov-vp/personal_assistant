from datetime import date

from pydantic import BaseModel

from src.cases.models.case_source import CaseSource


class TaskChange(BaseModel):
    due: date | None = None
    assignee: str | None = None
    external_id: str | None = None
    source: CaseSource
    summary: str
