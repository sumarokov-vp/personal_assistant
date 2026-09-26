from typing import Any, Protocol

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary


class IGmailMessageParser(Protocol):
    def parse_summary(self, raw_message: dict[str, Any]) -> MailSummary: ...

    def parse_message(self, raw_message: dict[str, Any]) -> MailMessage: ...
