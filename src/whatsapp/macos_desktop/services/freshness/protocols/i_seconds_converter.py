from datetime import datetime
from typing import Protocol


class ISecondsConverter(Protocol):
    def to_datetime(self, seconds: float) -> datetime: ...
