from pydantic import BaseModel


class TodoistDue(BaseModel):
    date: str
    string: str | None = None
    is_recurring: bool = False
