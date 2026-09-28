from typing import Any, Protocol

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.gmail.models.reply_target import ReplyTarget
from src.gmail.services.gmail_message_parser.mail_attachment_source import (
    MailAttachmentSource,
)


class IGmailMessageParser(Protocol):
    def parse_summary(self, raw_message: dict[str, Any]) -> MailSummary: ...

    def parse_message(self, raw_message: dict[str, Any]) -> MailMessage: ...

    def parse_thread(self, raw_thread: dict[str, Any]) -> list[MailMessage]: ...

    def parse_reply_target(self, raw_message: dict[str, Any]) -> ReplyTarget: ...

    def parse_attachment_source(
        self, raw_message: dict[str, Any], attachment_id: str
    ) -> MailAttachmentSource | None: ...

    def parse_attachment_bytes(self, raw_attachment: dict[str, Any]) -> bytes: ...
