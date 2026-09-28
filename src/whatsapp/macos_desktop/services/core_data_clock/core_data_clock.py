from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

CORE_DATA_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
DISPLAY_FORMAT = "%d.%m.%Y %H:%M"


class CoreDataClock:
    def __init__(self, timezone: ZoneInfo) -> None:
        self._timezone = timezone

    def to_seconds(self, moment: datetime) -> float:
        aware = moment if moment.tzinfo else moment.replace(tzinfo=self._timezone)
        return (aware - CORE_DATA_EPOCH).total_seconds()

    def to_datetime(self, seconds: float) -> datetime:
        return CORE_DATA_EPOCH + timedelta(seconds=seconds)

    def display(self, seconds: float | None) -> str:
        if seconds is None:
            return ""
        return (
            self.to_datetime(seconds)
            .astimezone(self._timezone)
            .strftime(DISPLAY_FORMAT)
        )
