from datetime import datetime
from zoneinfo import ZoneInfo

from src.scheduler.models.schedule import Schedule

WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def owner_moment(moment: datetime, timezone: ZoneInfo) -> str:
    local = moment.astimezone(timezone)
    return f"{WEEKDAYS[local.weekday()]} {local.strftime('%d.%m.%Y %H:%M')}"


def upcoming_moments(schedule: Schedule, timezone: ZoneInfo) -> list[str]:
    moments = schedule.upcoming or (
        [schedule.next_run_at] if schedule.next_run_at else []
    )
    return [owner_moment(moment, timezone) for moment in moments]


def periodicity(schedule: Schedule) -> str:
    return f"cron {schedule.cron} ({schedule.timezone})"
