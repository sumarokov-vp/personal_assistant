from datetime import date

from pydantic import BaseModel


class NewManagedTask(BaseModel):
    title: str
    description: str | None = None
    due: date | None = None
    deadline: date | None = None
