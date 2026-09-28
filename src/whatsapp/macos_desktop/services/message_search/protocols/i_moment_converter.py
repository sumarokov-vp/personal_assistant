from datetime import datetime
from typing import Protocol


class IMomentConverter(Protocol):
    def to_seconds(self, moment: datetime) -> float: ...
