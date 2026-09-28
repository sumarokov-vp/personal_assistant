from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from src.cases.models.case_source import CaseSource


class TaskClosure(BaseModel):
    status: Literal["done", "cancelled"]
    occurred_at: datetime
    source: CaseSource
    source_ref: str | None = None
    summary: str | None = None
