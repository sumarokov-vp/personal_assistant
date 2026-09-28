from typing import Protocol

from src.gmail.models.mail_message import MailMessage


class IGmailReader(Protocol):
    def get_message(self, message_id: str) -> MailMessage: ...
