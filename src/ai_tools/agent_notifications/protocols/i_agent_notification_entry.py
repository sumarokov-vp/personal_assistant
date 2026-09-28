from datetime import datetime
from typing import Protocol


class IAgentNotificationEntry(Protocol):
    @property
    def source(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def received_at(self) -> datetime: ...

    @property
    def file_label(self) -> str | None: ...
