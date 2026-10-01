from typing import Protocol

from src.scheduled_runs.models.scheduled_run import ScheduledRun


class IRunJournal(Protocol):
    def start(self, run_id: str, schedule_id: str, case_id: str) -> ScheduledRun: ...

    def finish(self, run_id: str, error: str | None) -> None: ...

    def mark_delivered(self, run_id: str) -> None: ...
