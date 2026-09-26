from typing import Any, Protocol

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.gmail.models.reply_target import ReplyTarget


class IGmailMessageParser(Protocol):
    def parse_summary(self, raw_message: dict[str, Any]) -> MailSummary: ...

    def parse_message(self, raw_message: dict[str, Any]) -> MailMessage: ...

    def parse_reply_target(self, raw_message: dict[str, Any]) -> ReplyTarget: ...
