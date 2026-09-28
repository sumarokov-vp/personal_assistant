from datetime import datetime
from typing import Protocol

from src.colleague_mail.models.colleague_message_type import ColleagueMessageType


class IIncomingMailJournal(Protocol):
    def record_incoming(
        self,
        message_id: str,
        sender: str,
        message_type: ColleagueMessageType,
        text: str,
        about_agent: str | None,
        in_reply_to: str | None,
        sent_at: datetime | None,
    ) -> bool: ...
