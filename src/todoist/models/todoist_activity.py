from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TodoistActivity(BaseModel):
    id: int | None = None
    object_type: str
    object_id: str
    event_type: str
    event_date: datetime
    extra_data: dict[str, Any] | None = None
