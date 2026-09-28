from datetime import date

from pydantic import BaseModel


class NewTask(BaseModel):
    due: date | None = None
    assignee: str
    external_id: str | None = None
