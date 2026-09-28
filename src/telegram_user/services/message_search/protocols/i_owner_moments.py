from datetime import datetime
from typing import Protocol


class IOwnerMoments(Protocol):
    def aware(self, moment: datetime | None) -> datetime | None: ...
