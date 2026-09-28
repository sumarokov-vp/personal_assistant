from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from src.ai_tools.colleague_mail.colleague_messages.protocols.i_colleague_message_entry import (
    IColleagueMessageEntry,
)


class IColleagueMessageJournal(Protocol):
    def messages_between(
        self,
        start: datetime,
        end: datetime,
        peer: str | None,
        message_type: str | None,
        limit: int,
    ) -> Sequence[IColleagueMessageEntry]: ...

    def unshown_incoming(
        self, peer: str | None, message_type: str | None, limit: int
    ) -> Sequence[IColleagueMessageEntry]: ...
