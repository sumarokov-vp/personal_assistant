from pydantic import BaseModel


class TodoistDeadline(BaseModel):
    date: str
