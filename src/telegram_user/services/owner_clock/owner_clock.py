from datetime import datetime
from zoneinfo import ZoneInfo

DISPLAY_FORMAT = "%d.%m.%Y %H:%M"


class OwnerClock:
    def __init__(self, timezone: ZoneInfo) -> None:
        self._timezone = timezone

    def display(self, moment: datetime | None) -> str:
        if moment is None:
            return ""
        return moment.astimezone(self._timezone).strftime(DISPLAY_FORMAT)

    def aware(self, moment: datetime | None) -> datetime | None:
        if moment is None or moment.tzinfo is not None:
            return moment
        return moment.replace(tzinfo=self._timezone)
