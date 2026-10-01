from typing import Literal

from pydantic import BaseModel

ScheduleStatusFilter = Literal["live", "active", "paused", "done", "cancelled", "all"]


class ScheduleQuery(BaseModel):
    status: ScheduleStatusFilter = "live"
    case_id: str | None = None
    limit: int = 50
