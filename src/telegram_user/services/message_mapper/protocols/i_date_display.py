from datetime import datetime
from typing import Protocol


class IDateDisplay(Protocol):
    def display(self, moment: datetime | None) -> str: ...
