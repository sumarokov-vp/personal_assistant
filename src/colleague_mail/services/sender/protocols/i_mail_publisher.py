from datetime import datetime
from typing import Protocol

from src.colleague_mail.models.colleague_message_type import ColleagueMessageType
from src.colleague_mail.services.entities.mail_send_outcome import MailSendOutcome


class IMailPublisher(Protocol):
    def publish(
        self,
        message_id: str,
        recipient: str,
        message_type: ColleagueMessageType,
        body: bytes,
        published_at: datetime,
    ) -> MailSendOutcome: ...
