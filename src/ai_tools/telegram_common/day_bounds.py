from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def start_of_day(day: date | None, timezone: ZoneInfo) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=timezone)


def start_of_next_day(day: date | None, timezone: ZoneInfo) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone)
