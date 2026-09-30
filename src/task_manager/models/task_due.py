from datetime import date, datetime

from pydantic import BaseModel


class TaskDue(BaseModel):
    on: date
    at: datetime | None = None
    text: str | None = None
