from collections.abc import Sequence
from typing import Protocol

from src.files.sources.mail_source.protocols.i_mail_attachment import IMailAttachment


class IMailWithAttachments(Protocol):
    @property
    def attachments(self) -> Sequence[IMailAttachment]: ...
