from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, available_timezones

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class ScheduleDue(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    v: Literal[1]
    run_id: str = Field(min_length=1)
    schedule_id: str = Field(min_length=1)
    user: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    task_event_id: str | None = None
    instruction: str = Field(min_length=1)
    kind: Literal["once", "periodic"]
    cron: str | None = None
    timezone: str
    scheduled_for: AwareDatetime
    fired_at: AwareDatetime
    late: bool

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        if value not in available_timezones():
            raise ValueError(f"unknown timezone {value!r}")
        return value

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def thread_id(self) -> str:
        return f"schedule:{self.run_id}"

    @property
    def late_minutes(self) -> int:
        return max(1, round(_seconds_between(self.scheduled_for, self.fired_at) / 60))


def _seconds_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds()
