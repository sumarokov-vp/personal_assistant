from typing import Protocol

from src.scheduler.models.schedule import Schedule
from src.scheduler.models.schedule_query import ScheduleQuery


class IScheduleLister(Protocol):
    def list_schedules(self, query: ScheduleQuery) -> list[Schedule]: ...
