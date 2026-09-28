from datetime import datetime
from typing import Protocol


class IInboundSync(Protocol):
    def sync(self, since: datetime) -> None: ...
