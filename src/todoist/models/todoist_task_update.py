from pydantic import BaseModel


class TodoistTaskUpdate(BaseModel):
    due_string: str | None = None
    due_lang: str | None = None
    deadline_date: str | None = None
    labels: list[str] | None = None
