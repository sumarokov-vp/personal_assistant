from datetime import datetime

from pydantic import BaseModel


class ScheduledRun(BaseModel):
    id: int
    run_id: str
    schedule_id: str
    case_id: str
    started_at: datetime
    finished_at: datetime | None
    delivered_at: datetime | None
    error: str | None
