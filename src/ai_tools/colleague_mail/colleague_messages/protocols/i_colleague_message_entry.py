from datetime import datetime
from typing import Protocol


class IColleagueMessageEntry(Protocol):
    @property
    def message_id(self) -> str: ...

    @property
    def direction(self) -> str: ...

    @property
    def peer(self) -> str: ...

    @property
    def type(self) -> str: ...

    @property
    def text(self) -> str: ...

    @property
    def about_agent(self) -> str | None: ...

    @property
    def in_reply_to(self) -> str | None: ...

    @property
    def sent_at(self) -> datetime | None: ...

    @property
    def received_at(self) -> datetime | None: ...
