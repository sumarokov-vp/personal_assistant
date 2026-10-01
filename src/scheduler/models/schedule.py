from datetime import datetime

from pydantic import BaseModel

from src.scheduler.models.schedule_kind import ScheduleKind
from src.scheduler.models.schedule_status import ScheduleStatus


class Schedule(BaseModel):
    id: str
    case_id: str
    task_event_id: str | None = None
    kind: ScheduleKind
    run_at: datetime | None = None
    cron: str | None = None
    timezone: str
    instruction: str
    status: ScheduleStatus
    next_run_at: datetime | None = None
    upcoming: list[datetime] = []
    last_run_at: datetime | None = None
    created_at: datetime
