from pydantic import BaseModel

from src.cases.models.case_status import CaseStatus


class CaseUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    status: CaseStatus | None = None
