from typing import Protocol

from src.files.sources.mail_source.protocols.i_mail_with_attachments import (
    IMailWithAttachments,
)


class IMailAttachments(Protocol):
    def get_message(self, message_id: str) -> IMailWithAttachments: ...

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes: ...
