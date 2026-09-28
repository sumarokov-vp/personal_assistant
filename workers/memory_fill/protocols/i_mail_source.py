from collections.abc import Sequence
from typing import Protocol

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary


class IMailSource(Protocol):
    def search_messages(self, query: str, limit: int) -> Sequence[MailSummary]: ...

    def get_message(self, message_id: str) -> MailMessage: ...
