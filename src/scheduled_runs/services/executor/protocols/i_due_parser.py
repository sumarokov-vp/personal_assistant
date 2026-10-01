from typing import Protocol

from src.scheduled_runs.services.entities.schedule_due import ScheduleDue


class IDueParser(Protocol):
    def parse(self, raw: bytes) -> ScheduleDue | None: ...
