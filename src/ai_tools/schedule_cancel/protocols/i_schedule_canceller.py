from typing import Protocol

from src.scheduler.models.schedule import Schedule


class IScheduleCanceller(Protocol):
    def cancel_schedule(self, schedule_id: str) -> Schedule: ...
