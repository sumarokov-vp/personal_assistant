from datetime import date

from pydantic import BaseModel, Field

DEFAULT_SEARCH_LIMIT = 50


class TaskSearch(BaseModel):
    text: str | None = None
    due_before: date | None = None
    overdue: bool = False
    by_assistant: bool = False
    limit: int = Field(default=DEFAULT_SEARCH_LIMIT, ge=1)
