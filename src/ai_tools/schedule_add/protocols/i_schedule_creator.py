from typing import Protocol

from src.scheduler.models.new_schedule import NewSchedule
from src.scheduler.models.schedule import Schedule


class IScheduleCreator(Protocol):
    def create_schedule(self, schedule: NewSchedule) -> Schedule: ...
